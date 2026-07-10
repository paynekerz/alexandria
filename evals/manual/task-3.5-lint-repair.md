# Manual test — Task 3.5 (vault lint & repair)

`scripts/vault_lint.py` validates every schema §9 invariant; `--repair` regenerates the derived files (`_index.md`, `_Concepts/`) from session frontmatter using the same renderers `vault.py` writes with. Authored content (session notes, glossary definitions) is never auto-modified.

## Baseline

```text
$ python vault_lint.py --vault ../docs/example-vault
clean: 0 findings
exit: 0
```

This run is also the deferred Task 3.1 DOD verification: the vault containing the 3.1/3.2 pipeline-saved sessions passes the automated lint.

## Defect injection (scratch copy of the example vault)

One deliberate defect per class, then lint:

```text
frontmatter Atlas/Sessions/2026-07-01 request-pipeline.md: depth 'expert' not in ('intro', 'practitioner', 'deep-dive')
glossary    Aurora/_glossary.md: orphaned entry 'Quantum Tunneling' — no session in this project teaches it
drift       Atlas/_index.md: differs from regeneration from frontmatter — fix with --repair
drift       Aurora/_index.md: differs from regeneration from frontmatter — fix with --repair
drift       _Concepts/Middleware.md: exists but concept is not taught in 2+ projects — removed by --repair
dead-link   Aurora/Sessions/2026-06-19 webhook-handling.md: [[2026-01-01 ghost-session]] — no note named '2026-01-01 ghost-session'

6 finding(s).  exit: 1
```

All four required classes caught (frontmatter schema, dead wiki-link, orphaned glossary entry, index/note drift), plus the invariant-6 violation (concept file without a 2-project concept). The `Atlas/_index.md` drift is the correct cascade of the depth edit — the stored index says `intro`, regeneration from the doctored frontmatter would not.

## Repair

1. **Guard**: `--repair` while session frontmatter is broken → refused, exit 2: *"regenerating derived files from broken frontmatter would spread the damage."*
2. Authored-content defects (bad depth, dead link, orphan entry) fixed by restoring the notes — the librarian/user's job, by design; ROADMAP scopes `--repair` to regenerating indexes.
3. `--repair` → regenerated all three `_index.md` + `_Concepts/Idempotency.md`, removed `_Concepts/Middleware.md`.
4. Final lint: `clean: 0 findings`, exit 0 — and `diff -r` against the pristine example vault: **byte-identical**.

## Regression tests

`scripts/tests/test_lint.py`: clean baseline pinned; one test per defect class; drift repair round-trips to pristine bytes; stale concept file removed; repair refusal under broken frontmatter. Full suite 46/46 green.
