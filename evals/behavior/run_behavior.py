#!/usr/bin/env python3
"""Run Alexandria behavior evals (ROADMAP 5.2).

Each case launches a real headless `claude -p` session inside an isolated
throwaway project root containing the fixture-shop codebase (a git repo),
the three Alexandria skills installed as project skills, the shared
scripts, and a freshly scaffolded vault. ALEXANDRIA_CONFIG_DIR points the
config read path at a per-run config, so nothing touches the developer's
real ~/.alexandria or vault.

Assertions are evaluated programmatically against the final response
text, the observed tool calls, and the vault filesystem (including a
vault_lint.py pass). Results persist incrementally after every case —
a crash never loses completed measurements (5.1 lesson).

Usage:
  python run_behavior.py --runs 3 --out ../results/5.2-behavior
  python run_behavior.py --runs 1 --cases post-save-lint   (smoke test)
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FIXTURE = HERE / "fixture-shop"
EVAL_SET = HERE / "behavior.evals.json"

_results_lock = threading.Lock()


def resolve_claude_cli():
    """Resolve the claude CLI to a real executable (same fix as run_eval.py):
    on Windows PATH lookup finds the npm .cmd shim, which Popen can't launch."""
    found = shutil.which("claude")
    if not found:
        return "claude"
    if found.lower().endswith((".cmd", ".bat", ".ps1")):
        exe = (
            Path(found).parent
            / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        )
        if exe.exists():
            return str(exe)
    return found


def make_isolated_root(base):
    """Build one throwaway project root + vault + config under `base`.

    Returns (run_root, vault_dir, env) ready for a claude -p session.
    """
    run_root = base / "fixture-shop"
    vault_dir = base / "Vault"
    config_dir = base / "alexandria-home"
    dot_claude = run_root / ".claude"

    shutil.copytree(FIXTURE, run_root)
    ignore = shutil.ignore_patterns("__pycache__", "tests", "*.pyc")
    for skill in ("alexandria-teach", "alexandria-librarian", "alexandria-recall"):
        shutil.copytree(REPO / "skills" / skill, dot_claude / "skills" / skill, ignore=ignore)
    shutil.copytree(REPO / "scripts", dot_claude / "scripts", ignore=ignore)
    shutil.copytree(REPO / "agents", dot_claude / "agents", ignore=ignore)
    shutil.copytree(REPO / "templates", dot_claude / "templates", ignore=ignore)

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    env["ALEXANDRIA_CONFIG_DIR"] = str(config_dir)
    # setup.py installs the filled teacher agent here; project-level agents
    # are discoverable by the headless session.
    env["ALEXANDRIA_AGENTS_DIR"] = str(dot_claude / "agents")
    env["PYTHONUTF8"] = "1"

    git = ["git", "-C", str(run_root), "-c", "user.name=behavior-eval",
           "-c", "user.email=eval@local"]
    subprocess.run(["git", "init", "-q", str(run_root)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(git + ["add", "-A"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(git + ["commit", "-qm", "fixture"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    setup = subprocess.run(
        [sys.executable, str(dot_claude / "scripts" / "setup.py"),
         "--vault-path", str(vault_dir), "--model", "inherit",
         "--depth", "intro", "--quiz", "off"],
        env=env, capture_output=True, text=True, encoding="utf-8",
    )
    if setup.returncode != 0:
        raise RuntimeError("setup.py failed: " + setup.stderr)
    return run_root, vault_dir, env


def parse_stream(stdout_text):
    """Extract final text, tool names, and metadata from stream-json output."""
    final = None
    is_error = False
    error_detail = None
    tools = []
    model = None
    last_assistant_text = ""
    cost = None
    duration_ms = None
    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = event.get("type")
        if etype == "system" and event.get("subtype") == "init":
            model = event.get("model")
        elif etype == "assistant":
            texts = []
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    tools.append(block.get("name", ""))
                elif block.get("type") == "text":
                    texts.append(block.get("text", ""))
            if texts:
                last_assistant_text = "\n".join(texts)
        elif etype == "result":
            is_error = bool(event.get("is_error"))
            res = event.get("result")
            if isinstance(res, str):
                final = res
            if is_error:
                error_detail = str(res)[:500]
            cost = event.get("total_cost_usd")
            duration_ms = event.get("duration_ms")
    if final is None:
        final = last_assistant_text
    return {
        "final": final or "",
        "tools": tools,
        "model": model,
        "is_error": is_error,
        "error_detail": error_detail,
        "cost_usd": cost,
        "duration_ms": duration_ms,
    }


def strip_save_block(text):
    """Remove the mandated save-offer block so the identical boilerplate
    doesn't inflate similarity between two lessons."""
    text = re.sub(r"\*\*Save this lesson\?\*\*.*", "", text, flags=re.S)
    text = re.sub(r"\*\*Draft concepts this session:\*\*.*", "", text, flags=re.S)
    return text


def jaccard(a, b):
    wa = set(re.findall(r"[a-z0-9]{3,}", strip_save_block(a).lower()))
    wb = set(re.findall(r"[a-z0-9]{3,}", strip_save_block(b).lower()))
    if not wa or not wb:
        return 1.0
    return len(wa & wb) / len(wa | wb)


def snippet(text, match, radius=80):
    start = max(0, match.start() - radius)
    return text[start:match.end() + radius].replace("\n", " ")


def eval_assertion(assertion, ctx):
    """Return {desc, type, passed, evidence}. `differs_from` is deferred."""
    atype = assertion["type"]
    out = {"type": atype, "desc": assertion.get("desc", atype)}
    final = ctx["final"]

    if atype == "final_regex":
        m = re.search(assertion["pattern"], final, re.I | re.S)
        out["passed"] = bool(m)
        out["evidence"] = snippet(final, m) if m else "pattern not found in final response"
    elif atype == "final_regex_any":
        hit = None
        for p in assertion["patterns"]:
            m = re.search(p, final, re.I | re.S)
            if m:
                hit = (p, m)
                break
        out["passed"] = hit is not None
        out["evidence"] = (
            "matched %r: %s" % (hit[0], snippet(final, hit[1])) if hit
            else "no pattern matched the final response"
        )
    elif atype == "final_not_regex":
        m = re.search(assertion["pattern"], final, re.I | re.S)
        out["passed"] = m is None
        out["evidence"] = "clean" if m is None else "forbidden match: " + snippet(final, m)
    elif atype == "tools_absent":
        offenders = [t for t in assertion["tools"] if t in ctx["tools"]]
        out["passed"] = not offenders
        out["evidence"] = "offending tool calls: %s" % offenders if offenders else "none of %s called" % assertion["tools"]
    elif atype == "tools_any_present":
        hits = [t for t in assertion["tools"] if t in ctx["tools"]]
        out["passed"] = bool(hits)
        out["evidence"] = "called: %s" % hits if hits else "none of %s called (tools seen: %s)" % (assertion["tools"], sorted(set(ctx["tools"])))
    elif atype == "any_of":
        subs = [eval_assertion(a, ctx) for a in assertion["assertions"]]
        out["passed"] = any(s["passed"] for s in subs)
        out["evidence"] = "; ".join("[%s] %s: %s" % ("PASS" if s["passed"] else "fail", s["desc"], s["evidence"]) for s in subs)
    elif atype == "vault_glob":
        matches = sorted(str(p.relative_to(ctx["vault"])) for p in ctx["vault"].glob(assertion["pattern"]))
        out["passed"] = len(matches) >= assertion.get("min", 1)
        out["evidence"] = "matches: %s" % matches if matches else "no match for %s in vault" % assertion["pattern"]
    elif atype == "vault_lint_clean":
        lint = subprocess.run(
            [sys.executable, str(ctx["run_root"] / ".claude" / "scripts" / "vault_lint.py"),
             "--vault", str(ctx["vault"])],
            env=ctx["env"], capture_output=True, text=True, encoding="utf-8",
        )
        out["passed"] = lint.returncode == 0
        out["evidence"] = ("exit 0 (clean)" if lint.returncode == 0
                           else "exit %d: %s" % (lint.returncode, (lint.stdout + lint.stderr).strip()[:800]))
    elif atype == "differs_from":
        out["passed"] = None  # resolved by resolve_pair_assertions once both cases finish
        out["evidence"] = "deferred"
    else:
        out["passed"] = False
        out["evidence"] = "unknown assertion type"
    return out


def run_case(case, timeout, run_dir):
    """Execute one case in a fresh isolated root; return the case result dict."""
    base = Path(tempfile.mkdtemp(prefix="behavior-eval-"))
    started = time.time()
    result = {"id": case["id"], "category": case["category"], "skill": case["skill"], "error": None}
    try:
        run_root, vault_dir, env = make_isolated_root(base)
        cmd = [
            resolve_claude_cli(),
            "-p", case["prompt"],
            "--output-format", "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
            # Exclude user-level settings so personal hooks/plugins don't
            # contaminate measurement (same rationale as 5.1).
            "--setting-sources", "project,local",
        ]
        try:
            proc = subprocess.run(
                cmd, cwd=str(run_root), env=env, capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            (run_dir / (case["id"] + ".jsonl")).write_bytes(e.stdout or b"")
            result["error"] = "timeout after %ds" % timeout
            return result

        stdout_text = (proc.stdout or b"").decode("utf-8", errors="replace")
        (run_dir / (case["id"] + ".jsonl")).write_text(stdout_text, encoding="utf-8")
        if proc.returncode != 0 or proc.stderr:
            (run_dir / (case["id"] + ".stderr.txt")).write_text(
                (proc.stderr or b"").decode("utf-8", errors="replace"), encoding="utf-8")

        parsed = parse_stream(stdout_text)
        result["model"] = parsed["model"]
        result["cost_usd"] = parsed["cost_usd"]
        result["duration_s"] = round((parsed["duration_ms"] or 0) / 1000.0, 1)
        result["tools"] = sorted(set(parsed["tools"]))
        result["final"] = parsed["final"]
        if parsed["is_error"] or (proc.returncode != 0 and not parsed["final"]):
            # API-rejected/errored runs carry no signal: excluded, never
            # counted as behavior failures (5.1 lesson).
            result["error"] = parsed["error_detail"] or ("claude exited %d" % proc.returncode)
            return result

        ctx = {"final": parsed["final"], "tools": parsed["tools"],
               "vault": vault_dir, "run_root": run_root, "env": env}
        result["assertions"] = [eval_assertion(a, ctx) for a in case["assertions"]]
        return result
    except Exception as e:  # noqa: BLE001 — harness fault, recorded not raised
        result["error"] = "harness error: %r" % e
        return result
    finally:
        result["wall_s"] = round(time.time() - started, 1)
        shutil.rmtree(base, ignore_errors=True)


def resolve_pair_assertions(cases_by_id):
    """Fill in deferred differs_from assertions once all cases of a run exist."""
    for case in cases_by_id.values():
        for a_spec, a_res in zip_assertions(case):
            if a_spec["type"] != "differs_from":
                continue
            other = cases_by_id.get(a_spec["other"])
            if case.get("error") or not other or other.get("error"):
                a_res["passed"] = None
                a_res["evidence"] = "unresolvable: paired case errored or missing"
                continue
            j = jaccard(case.get("final", ""), other.get("final", ""))
            a_res["passed"] = j <= a_spec["max_jaccard"]
            a_res["evidence"] = "jaccard=%.2f vs %s (threshold %.2f)" % (j, a_spec["other"], a_spec["max_jaccard"])


def zip_assertions(case_result):
    spec = next(c for c in EVAL_CASES if c["id"] == case_result["id"])
    return list(zip(spec["assertions"], case_result.get("assertions", [])))


def case_passed(case_result):
    if case_result.get("error"):
        return None
    asserts = case_result.get("assertions", [])
    if any(a["passed"] is None for a in asserts):
        return None
    return all(a["passed"] for a in asserts)


def summarize(runs):
    per_case = {}
    for run in runs:
        for c in run["cases"]:
            entry = per_case.setdefault(c["id"], {"pass": 0, "fail": 0, "error": 0})
            p = case_passed(c)
            if p is None:
                entry["error"] += 1
            elif p:
                entry["pass"] += 1
            else:
                entry["fail"] += 1
    flakes = [cid for cid, e in per_case.items() if e["pass"] and e["fail"]]
    all_green = all(e["fail"] == 0 and e["error"] == 0 and e["pass"] > 0 for e in per_case.values()) if per_case else False
    return {"per_case": per_case, "flaky_cases": flakes, "all_runs_green": all_green}


def main():
    parser = argparse.ArgumentParser(description="Run Alexandria behavior evals (ROADMAP 5.2)")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--cases", default=None, help="comma-separated case ids (default: all)")
    parser.add_argument("--num-workers", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=900, help="seconds per case session")
    parser.add_argument("--out", default=str(REPO / "evals" / "results" / "5.2-behavior"))
    args = parser.parse_args()

    global EVAL_CASES
    eval_set = json.loads(EVAL_SET.read_text(encoding="utf-8"))
    EVAL_CASES = eval_set["cases"]
    cases = EVAL_CASES
    if args.cases:
        wanted = {c.strip() for c in args.cases.split(",")}
        cases = [c for c in EVAL_CASES if c["id"] in wanted]
        missing = wanted - {c["id"] for c in cases}
        if missing:
            print("Unknown case ids: %s" % sorted(missing), file=sys.stderr)
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
            "task": "5.2-behavior",
            "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "repo_commit": repo_commit,
            "eval_set": str(EVAL_SET.relative_to(REPO)),
            "runs_requested": args.runs,
            "cases": [c["id"] for c in cases],
            "timeout_s": args.timeout,
            "num_workers": args.num_workers,
        },
        "runs": [],
    }

    def persist():
        with _results_lock:
            results_file.write_text(json.dumps(output, indent=2), encoding="utf-8")

    for run_no in range(1, args.runs + 1):
        run_dir = out_dir / ("run%d" % run_no)
        run_dir.mkdir(exist_ok=True)
        run_record = {"run": run_no, "cases": []}
        output["runs"].append(run_record)
        print("=== run %d/%d ===" % (run_no, args.runs), flush=True)
        with ThreadPoolExecutor(max_workers=args.num_workers) as pool:
            futures = {pool.submit(run_case, c, args.timeout, run_dir): c for c in cases}
            for fut in as_completed(futures):
                res = fut.result()
                run_record["cases"].append(res)
                persist()
                status = "ERROR" if res.get("error") else "done"
                print("  [%s] %s (%.0fs)%s" % (
                    status, res["id"], res.get("wall_s", 0),
                    " — " + str(res.get("error"))[:120] if res.get("error") else ""), flush=True)
        resolve_pair_assertions({c["id"]: c for c in run_record["cases"]})
        for c in run_record["cases"]:
            p = case_passed(c)
            label = "PASS" if p else ("ERROR" if p is None else "FAIL")
            print("  %s %s" % (label, c["id"]), flush=True)
            if p is False:
                for a in c.get("assertions", []):
                    if a["passed"] is False:
                        print("      failed: %s — %s" % (a["desc"], a["evidence"][:200]), flush=True)
        persist()

    output["summary"] = summarize(output["runs"])
    persist()
    print(json.dumps(output["summary"], indent=2))
    print("Results: %s" % results_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
