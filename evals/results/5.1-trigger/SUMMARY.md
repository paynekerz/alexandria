# Task 5.1 — Trigger Eval Results

Date: 2026-07-16 · Model under test: `claude-fable-5` · 20 queries per skill (10 positive / 10 negative), 3 runs per query, run via `run_loop.py` (`--max-iterations 1`, baseline descriptions, no optimization applied).

## DOD scorecard

| Skill | Positive trigger rate (DOD ≥90%) | False-trigger rate (DOD ≤5%) | Verdict |
|---|---|---|---|
| alexandria-teach | 30/30 = **100%** | 0/30 = **0%** | PASS |
| alexandria-librarian | 29/30 = **96.7%** | 0/30 = **0%** | PASS |
| alexandria-recall | 30/30 = **100%** | 0/27 = **0%** ¹ | PASS |

¹ 6 of recall's 30 negative runs errored on the plan's five-hour session limit and carry no signal (excluded, never counted as "did not trigger"). The one fully-errored query (`find all TODO comments…`) was rerun standalone after the window reset: 0/3 false triggers (`alexandria-recall/2026-07-16_183440/patchup-results.json`). Valid negative runs total 27.

The only positive miss anywhere: librarian's `"yes — save that one to my alexandria library"` triggered 2/3. It is the vaguest accept-the-offer phrasing in the set (cold context, no antecedent lesson); still passes the per-query threshold.

**Description optimization (the `improve_description` loop) was not run** — all three baseline descriptions already clear both DOD thresholds, so there were no failures to optimize against. The loop remains available for Phase 7.2.

## Evidence

- Eval sets: `evals/trigger/<skill>.trigger.json`
- Raw results: `evals/results/5.1-trigger/<skill>/<timestamp>/results.json` (+ `report.html` per run)
- Reviewer-facing HTML reports: `evals/results/5.1-trigger/<skill>-report.html`
- Valid result dirs: teach `2026-07-16_083349`, librarian `2026-07-16_182540`, recall `2026-07-16_183440`

## Eval-set design notes

- ROADMAP 5.1's example positives ("teach me this file", "explain this like I'm new") predate Locked Decision 15 (explicit invocation only). Positives therefore all name Alexandria (or its slash command); those bare phrasings appear in the **negative** sets instead, as near-misses that must not trigger.
- Each skill's negatives include one cross-skill confusion case (e.g. "alexandria, teach me…" inside librarian's and recall's negative sets). All scored 0 false triggers.
- Runs execute in an isolated throwaway project root with `--setting-sources project,local`, so personal hooks/plugins on this machine don't contaminate measurement.

## Harness fixes required (vendored `evals/tooling/`)

The upstream skill-creator tooling needed five fixes to produce valid data on this machine; all are in the same commit as these results:

1. `select.select()` on a pipe is Unix-only → reader-thread + queue in `run_eval.py`.
2. `claude` resolves to an npm `.cmd` shim `Popen` can't launch → resolve to the package's native `claude.exe`.
3. Default `cp1252` encoding crashed report writes (✓/✗ chars) and mojibake'd UTF-8 eval sets → explicit `encoding="utf-8"` on all read/write paths (plus `PYTHONUTF8=1` at launch).
4. **Concurrency pollution**: parallel workers shared `.claude/commands/`, so each eval session saw N near-identical command files and invoked an arbitrary one — measured recall collapsed to ~1/N (observed 13% with 8 workers). Each run now gets its own temp project root.
5. **Silent error runs**: API-rejected runs (session limit) were counted as "did not trigger", producing a fake 0% recall. Errored runs now return `None`, are excluded from rates, and are surfaced as warnings + `errored_runs` in results.
6. `generate_report.py` crashed with `--holdout 0` (`test_results` is `None`, and `.get(key, default)` doesn't apply when the key exists as `None`).

Lesson for 5.2/5.3: `run_loop.py` only persists results at the end of an iteration — a crash after measurement loses all runs. Validate the full persistence path with a mini run before any large batch.
