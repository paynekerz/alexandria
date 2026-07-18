#!/usr/bin/env python3
"""Token budget benchmarks (ROADMAP 5.3).

Measures real token usage for the three representative Alexandria session
types, each a live headless `claude -p` session in the same isolated
fixture-shop root the 5.2 behavior evals use:

  simple-walkthrough    teach one small file, no external sources
  concept-heavy-sources teach with Tier 1 external source retrieval
  recall-assisted       teach a topic already in the library (vault
                        pre-seeded via vault.py save-session), so recall
                        surfaces the prior session and teach links it

Token figures come from the stream-json result event's `modelUsage`,
summed across every model in the session — this includes the pinned
teacher subagent and any helper models, which the top-level `usage`
block (main thread only) misses.

A run only counts toward the baseline if it was *representative*
(walkthrough fetched nothing, sources session actually fetched, recall
session actually wiki-linked prior material). Errored or
non-representative runs are excluded, never averaged in — a baseline
from a wrong-shaped session would be noise (5.1/5.2 lesson).

Usage:
  python run_token_benchmark.py --runs 3                 measure, write results
  python run_token_benchmark.py --check                  release-checklist mode:
      re-measure and compare per-type mean total tokens against
      baseline.json; any regression >20% exits 1 (blocks release)
"""
import argparse
import datetime
import json
import subprocess
import sys
import tempfile
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE_FILE = HERE / "baseline.json"

sys.path.insert(0, str(HERE.parent / "behavior"))
import run_behavior as rb  # noqa: E402 — shared 5.2 isolation harness

REGRESSION_THRESHOLD = 0.20

SEED_LESSON = (
    "The verify() function in src/verify.php decides whether an incoming "
    "webhook really came from the payment gateway. It recomputes an HMAC-SHA256 "
    "signature over the raw request payload using the shared secret — this is "
    "[[fixture-shop/_glossary#HMAC Signature Verification|HMAC signature "
    "verification]] — then compares that against the signature header the "
    "sender provided. The comparison uses PHP's hash_equals(), a "
    "[[fixture-shop/_glossary#Constant-Time Comparison|constant-time "
    "comparison]], so an attacker cannot learn the correct signature byte by "
    "byte from response timing."
)

SESSIONS = [
    {
        "id": "simple-walkthrough",
        "desc": "one-file walkthrough, no external sources",
        "prompt": ("alexandria, teach me src/verify.php at intro depth. "
                   "Just a simple walkthrough of this one file — no extras."),
        "seed": False,
    },
    {
        "id": "concept-heavy-sources",
        "desc": "concept-heavy lesson with Tier 1 source retrieval",
        "prompt": ("alexandria, teach me src/webhook.php at intro depth. The "
                   "concepts behind it (HMAC signatures, webhooks) are completely "
                   "new to me — please include a good external resource where I "
                   "can study them properly."),
        "seed": False,
    },
    {
        "id": "recall-assisted",
        "desc": "topic already in the library; recall links, teach covers the delta",
        "prompt": ("alexandria, teach me how src/verify.php decides whether a "
                   "webhook is authentic — intro depth."),
        "seed": True,
    },
]


def seed_vault(run_root, env):
    """Pre-save one session note so recall has prior material to surface."""
    scripts = run_root / ".claude" / "scripts"
    commit = subprocess.run(
        ["git", "-C", str(run_root), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True).stdout.strip()
    payload = {
        "project": "fixture-shop",
        "title": "Webhook signature verification",
        "slug": "webhook-signature-verification",
        "date": "2026-07-10",
        "depth": "intro",
        "concepts": [
            {"name": "HMAC Signature Verification",
             "definition": ("Proving a message really came from a trusted sender by "
                            "recomputing a keyed hash (HMAC) over the message with a "
                            "shared secret and checking it matches the signature the "
                            "sender attached.")},
            {"name": "Constant-Time Comparison",
             "definition": ("Comparing two secret values in a way that always takes "
                            "the same amount of time regardless of where they differ, "
                            "so an attacker cannot learn the secret from response "
                            "timing.")},
        ],
        "files": ["src/verify.php"],
        "commit": commit,
        "sources": [],
        "lesson": SEED_LESSON,
    }
    for cmd in (["ensure-project", "fixture-shop"], ["save-session"]):
        proc = subprocess.run(
            [sys.executable, str(scripts / "vault.py")] + cmd,
            input=json.dumps(payload) if cmd == ["save-session"] else None,
            env=env, capture_output=True, text=True, encoding="utf-8",
        )
        if proc.returncode != 0:
            raise RuntimeError("vault.py %s failed: %s" % (cmd[0], proc.stderr))


def parse_usage(stdout_text):
    """Pull modelUsage + session metadata from the stream-json result event."""
    for line in stdout_text.splitlines():
        line = line.strip()
        if not line or '"type":"result"' not in line.replace(" ", ""):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "result":
            continue
        per_model, totals = {}, {"input": 0, "output": 0, "cacheRead": 0,
                                 "cacheCreation": 0, "costUSD": 0.0}
        for model, u in (event.get("modelUsage") or {}).items():
            row = {
                "input": u.get("inputTokens", 0),
                "output": u.get("outputTokens", 0),
                "cacheRead": u.get("cacheReadInputTokens", 0),
                "cacheCreation": u.get("cacheCreationInputTokens", 0),
                "costUSD": u.get("costUSD", 0.0),
            }
            per_model[model] = row
            for k in totals:
                totals[k] += row[k]
        totals["total"] = (totals["input"] + totals["output"]
                           + totals["cacheRead"] + totals["cacheCreation"])
        return {
            "perModel": per_model,
            "totals": totals,
            "num_turns": event.get("num_turns"),
            "duration_s": round((event.get("duration_ms") or 0) / 1000.0, 1),
        }
    return None


def representative(session_id, parsed):
    """Was this run the session shape it claims to measure?"""
    tools, final = parsed["tools"], parsed["final"]
    fetched = any(t in tools for t in ("WebFetch", "WebSearch"))
    if session_id == "simple-walkthrough" and fetched:
        return False, "external fetch on a no-extras walkthrough"
    if session_id == "concept-heavy-sources" and not fetched:
        return False, "no external fetch — not a sources session"
    if session_id == "recall-assisted" and "[[" not in final:
        return False, "no wiki-link to prior material — recall did not assist"
    if "**Save this lesson?**" not in final:
        return False, "no save offer — session ended abnormally"
    return True, "ok"


def run_session(session, timeout, run_dir, run_no):
    base = Path(tempfile.mkdtemp(prefix="token-bench-"))
    started = time.time()
    result = {"id": session["id"], "run": run_no, "error": None}
    try:
        run_root, vault_dir, env = rb.make_isolated_root(base)
        if session["seed"]:
            seed_vault(run_root, env)
        cmd = [
            rb.resolve_claude_cli(),
            "-p", session["prompt"],
            "--output-format", "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
            "--setting-sources", "project,local",
        ]
        try:
            proc = subprocess.run(cmd, cwd=str(run_root), env=env,
                                  capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            (run_dir / ("%s.run%d.jsonl" % (session["id"], run_no))).write_bytes(e.stdout or b"")
            result["error"] = "timeout after %ds" % timeout
            return result

        stdout_text = (proc.stdout or b"").decode("utf-8", errors="replace")
        (run_dir / ("%s.run%d.jsonl" % (session["id"], run_no))).write_text(
            stdout_text, encoding="utf-8")

        parsed = rb.parse_stream(stdout_text)
        usage = parse_usage(stdout_text)
        result["model"] = parsed["model"]
        result["tools"] = sorted(set(parsed["tools"]))
        if parsed["is_error"] or usage is None:
            result["error"] = parsed["error_detail"] or "no result event / API error"
            return result
        ok, why = representative(session["id"], parsed)
        result["representative"] = ok
        result["representative_detail"] = why
        result["usage"] = usage
        return result
    except Exception as e:  # noqa: BLE001 — harness fault, recorded not raised
        result["error"] = "harness error: %r" % e
        return result
    finally:
        result["wall_s"] = round(time.time() - started, 1)
        shutil.rmtree(base, ignore_errors=True)


def valid(res):
    return not res.get("error") and res.get("representative")


def aggregate(results, sessions=None):
    """Per-session-type mean/min/max of total tokens over valid runs."""
    agg = {}
    for s in (sessions or SESSIONS):
        rows = [r for r in results if r["id"] == s["id"] and valid(r)]
        totals = [r["usage"]["totals"]["total"] for r in rows]
        entry = {"desc": s["desc"], "valid_runs": len(totals)}
        if totals:
            entry.update({
                "total_tokens_mean": round(sum(totals) / len(totals)),
                "total_tokens_min": min(totals),
                "total_tokens_max": max(totals),
                "output_tokens_mean": round(sum(
                    r["usage"]["totals"]["output"] for r in rows) / len(rows)),
                "cost_usd_mean": round(sum(
                    r["usage"]["totals"]["costUSD"] for r in rows) / len(rows), 4),
            })
        agg[s["id"]] = entry
    return agg


def check_against_baseline(agg):
    """Release-checklist gate: >20% mean-total regression on any type fails."""
    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    failures = []
    print("\n=== Release check vs %s (recorded %s) ===" % (
        BASELINE_FILE.name, baseline["metadata"]["recorded"]))
    for sid, base_entry in baseline["baselines"].items():
        base_mean = base_entry["total_tokens_mean"]
        cur = agg.get(sid, {})
        if not cur.get("valid_runs"):
            failures.append(sid)
            print("  %-24s FAIL — no valid runs to compare" % sid)
            continue
        cur_mean = cur["total_tokens_mean"]
        delta = (cur_mean - base_mean) / base_mean
        verdict = "FAIL" if delta > REGRESSION_THRESHOLD else "ok"
        if delta > REGRESSION_THRESHOLD:
            failures.append(sid)
        print("  %-24s %s — baseline %d, now %d (%+.1f%%; limit +%.0f%%)" % (
            sid, verdict, base_mean, cur_mean, delta * 100,
            REGRESSION_THRESHOLD * 100))
    if failures:
        print("REGRESSION: %s exceed the +20%% token budget — release blocked." % failures)
        return 1
    print("All session types within budget.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Alexandria token benchmarks (ROADMAP 5.3)")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--num-workers", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--out", default=str(REPO / "evals" / "results" / "5.3-benchmark"))
    parser.add_argument("--check", action="store_true",
                        help="compare fresh measurements against baseline.json; exit 1 on >20%% regression")
    parser.add_argument("--only", default=None,
                        help="comma-separated session ids (default: all three)")
    args = parser.parse_args()

    sessions = SESSIONS
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        sessions = [s for s in SESSIONS if s["id"] in wanted]
        missing = wanted - {s["id"] for s in sessions}
        if missing:
            print("Unknown session ids: %s" % sorted(missing), file=sys.stderr)
            return 2

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_dir = Path(args.out) / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    results_file = out_dir / "results.json"

    repo_commit = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True).stdout.strip()
    output = {
        "metadata": {
            "task": "5.3-token-benchmark",
            "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "repo_commit": repo_commit,
            "runs_per_type": args.runs,
            "mode": "check" if args.check else "measure",
        },
        "results": [],
    }

    def persist():
        results_file.write_text(json.dumps(output, indent=2), encoding="utf-8")

    jobs = [(s, n) for s in sessions for n in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=args.num_workers) as pool:
        futures = {pool.submit(run_session, s, args.timeout, out_dir, n): (s, n)
                   for s, n in jobs}
        for fut in as_completed(futures):
            res = fut.result()
            output["results"].append(res)
            persist()
            if res.get("error"):
                label = "ERROR: " + str(res["error"])[:120]
            elif not res.get("representative"):
                label = "EXCLUDED: " + res["representative_detail"]
            else:
                label = "%d total tokens" % res["usage"]["totals"]["total"]
            print("  [%s run %d] %s (%.0fs)" % (res["id"], res["run"], label,
                                                res.get("wall_s", 0)), flush=True)

    output["aggregate"] = aggregate(output["results"], sessions)
    persist()
    print(json.dumps(output["aggregate"], indent=2))
    print("Results: %s" % results_file)

    if args.check:
        return check_against_baseline(output["aggregate"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
