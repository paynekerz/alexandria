# Token cost of a retrieval pass (ROADMAP 4.1 DOD)

Measured 2026-07-13 against `docs/example-vault/` (3 projects, 6 sessions). Character counts are exact (PowerShell `.Length` on captured output); token figures are **estimates** at the ~4 characters/token heuristic for English/JSON text — the real tokenizer is not available offline, so these are labeled estimates, not measurements (Axiom 3).

## What a retrieval pass costs

One pass = one `recall.py search` invocation (the command line, ~40 chars) plus its JSON output read back into context:

| Scenario | Query | Output chars | Est. tokens |
|---|---|---|---|
| Single match + glossary hit | `Atlas` / "idempotency" | 750 | ~190 |
| No match (empty result + taught list) | `Aurora` / "quantum entanglement" | 242 | ~60 |
| Multi-match (2 sessions) | `Alexandria` / "how session notes get written and saved safely" | 1,351 | ~340 |

**Typical pass: ~200 tokens; worst observed: ~350.** Output grows with *match count* (one compact object per matched session), not with vault size — an unmatched 100-session vault costs the same ~60 tokens as an unmatched 4-session one, plus one line per glossary concept in `taughtConcepts`.

Fixed overhead when the skill itself is invoked: `SKILL.md` body is 5,216 chars ≈ 1,300 tokens, loaded once per invocation. When `alexandria-teach` runs the search as its Step 2, only the command + output cost applies.

## Why the script, not raw reads

The pre-4.1 alternative — reading `_glossary.md`, `_index.md`, and the matched session note directly — costs 3,381 chars ≈ 850 tokens for the same single-match lookup on this small vault, and that figure grows linearly with sessions taught (the index and glossary grow with every save; the model would also read full note bodies it doesn't need). The script keeps note bodies out of context entirely: recall reads a summary, and opens a specific note only when the user asks what that note says.

## Re-measuring

```powershell
$out = python scripts\recall.py --vault docs\example-vault search Atlas --query "idempotency" | Out-String
$out.Length   # chars; divide by 4 for the token estimate
```

Phase 5.3 replaces these estimates with tokenizer-measured baselines in `docs/BENCHMARKS.md`.
