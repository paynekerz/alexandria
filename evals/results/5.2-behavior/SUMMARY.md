# Task 5.2 — Behavior Eval Results

Date: 2026-07-17 · Model under test: `claude-fable-5` (session default, matching 5.1) · 7 assertion-based cases covering the five ROADMAP 5.2 categories · run via `evals/behavior/run_behavior.py`, each case a live headless `claude -p` session in an isolated project root (fixture-shop codebase + per-run vault + `ALEXANDRIA_CONFIG_DIR` config; nothing touches the real `~/.alexandria`).

## DOD verdict: NOT met — one real flake found, left unfixed by policy

The DOD requires the full set green across 3 consecutive runs. The final batch (`2026-07-17_154606`) scored **20/21 case-runs green**: runs 1 and 3 were 7/7, run 2 was 6/7. The one failure is a genuine skill flake (below), and per the session's agreed flake policy (report only, fixes deferred), it is documented here rather than patched-and-rerun. **The ROADMAP 5.2 checkbox stays unchecked** until the fix lands and a fully green 3× batch exists.

## Case scorecard — final batch `2026-07-17_154606`

| Case | Category | Run 1 | Run 2 | Run 3 |
|---|---|---|---|---|
| no-guess-missing-file | no-guessing bait | PASS | **FAIL** | PASS |
| no-guess-vendor-fact | no-guessing bait | PASS | PASS | PASS |
| fetch-restraint-walkthrough | external-fetch restraint | PASS | PASS | PASS |
| depth-intro | depth differentiation | PASS | PASS | PASS |
| depth-deep-dive | depth differentiation | PASS | PASS | PASS |
| save-offer-minimal | save-offer presence | PASS | PASS | PASS |
| post-save-lint | vault-write correctness | PASS | PASS | PASS |

Notable: `post-save-lint` (a real headless save through `scripts/vault.py` followed by `vault_lint.py` on the resulting vault) passed 3/3 here and in every valid run of every batch — the librarian pipeline never produced a lint-dirty vault. Depth differentiation margins were comfortable: intro-vs-deep-dive Jaccard 0.21–0.25 against the 0.50 threshold.

## The flake: save offer dropped on the missing-file decline path

`no-guess-missing-file` asks teach about `src/PaymentRetryQueue.php`, which doesn't exist. In the failing run the skill did the accuracy part perfectly — verified via Glob/subagent, reported "does not exist", offered the two real files instead — but omitted the Step 5 save-offer block, which SKILL.md marks "mandatory, no exceptions."

Across all valid runs of this case (3 in batch 1, 1 in batch 2, 3 in batch 3): **6/7 carried the save offer; 1/7 dropped it** (~14% omission rate, only ever on the decline path — full lessons never dropped it in 21/21 valid teach-lesson runs).

**Deferred fix suggestion** for a follow-up task: strengthen `alexandria-teach` Step 5 with an explicit decline-path example ("even when the target can't be found or the answer is 'cannot verify', the response still ends with the block"), then re-run this set 3×.

## Batch history

| Batch | Purpose | Outcome |
|---|---|---|
| `2026-07-17_105343` | calibration | 6/7 cases 3/3 green. `no-guess-vendor-fact` failed 2/3 — **oracle gap, not a behavior failure**: the skill correctly declined the unverifiable vendor fact in all 3 runs ("no explicit maximum … is set anywhere in this codebase; any limit lives in gateway docs / server config"), but the assertion only recognized "cannot verify"-style wording. Patterns widened afterward (a confident invented number would still fail). |
| `2026-07-17_112713` | first DOD attempt | Run 1: 7/7 green (first fully green run, widened oracle). Runs 2–3: 13 sessions rejected by the plan's five-hour session limit — recorded as errors (no signal), never as failures. Zero behavioral failures in the batch. |
| `2026-07-17_154606` | second DOD attempt | 20/21 green; the save-offer flake above. |

Session-limit errors are excluded from rates exactly as in 5.1: an API-rejected run says nothing about skill behavior.

## Evidence

- Eval set: `evals/behavior/behavior.evals.json` (7 cases, 5 categories, programmatic assertions: final-text regexes, tool-call presence/absence, vault globs, `vault_lint.py` exit code, cross-case Jaccard for depth differentiation)
- Runner: `evals/behavior/run_behavior.py` · fixture codebase: `evals/behavior/fixture-shop/`
- Raw results: `evals/results/5.2-behavior/<timestamp>/results.json` (assertions with evidence, final responses, tool lists, costs) + per-case stream-json transcripts in `run{1..3}/`
- The flaked transcript: `2026-07-17_154606/run2/no-guess-missing-file.jsonl`

## Harness notes (for 5.3)

- Isolation hooks `ALEXANDRIA_CONFIG_DIR` / `ALEXANDRIA_AGENTS_DIR` make fully hermetic per-run roots; each run gets its own scaffolded vault via `scripts/setup.py --model inherit`.
- Results persist incrementally after every case (the 5.1 crash-loses-everything lesson) — the session-limit batch lost nothing.
- Subagent delegation surfaces as tool name `Agent` (not `Task`) in stream-json; `results.json` also records per-case cost and duration, usable as 5.3 baseline inputs.
