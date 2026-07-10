# Manual test — Task 3.1 (session save pipeline)

Everything below ran through `scripts/vault.py save-session` — no freehand file edits. The lint verification required by the 3.1 DOD happens when `vault_lint.py` lands (Task 3.5); until then this records the raw files, per the internal task prompts.

## Setup

A scratch `ALEXANDRIA_CONFIG_DIR` whose `config.json` points `vaultPath` at `docs/example-vault/`, so the demo exercises the real config → vault path without touching the user's live vault.

## Input

Payload (stdin JSON, format per `skills/alexandria-librarian/references/payload.md`): project `Alexandria`, title "How vault writes stay inside the vault", depth `intro`, concepts `Path Traversal` + `Atomic Write` (both with intro-level definitions), files `scripts/vault.py`, commit `ceb9a01` (repo HEAD at teach time), sources `[]` (simple code walkthrough → zero external fetches, per the 2.3 rules).

## Command and output

```text
$ python vault.py save-session < payload-3.1.json
note:     ...\docs\example-vault\Alexandria\Sessions\2026-07-09 vault-write-safety.md
glossary: added Path Traversal, Atomic Write
index:    ...\docs\example-vault\Alexandria\_index.md
concepts: none — no saved concept spans 2+ projects
exit: 0
```

## What the DOD asks vs. what landed

| DOD requirement | Result |
|---|---|
| Note with valid frontmatter | [Sessions/2026-07-09 vault-write-safety.md](../../docs/example-vault/Alexandria/Sessions/2026-07-09%20vault-write-safety.md) — all §3 fields, fixed order, `schemaVersion: 1`, frontmatter round-trips through `parse_frontmatter`/`serialize_frontmatter` byte-identically (unit-tested) |
| Glossary entries wiki-linked from every usage in the note | [_glossary.md](../../docs/example-vault/Alexandria/_glossary.md) — both concepts got entries; the note's lesson prose links both (`[[Alexandria/_glossary#Path Traversal\|...]]`, `[[Alexandria/_glossary#Atomic Write\|...]]`); the save script **rejects** payloads whose lesson omits a concept's glossary link |
| Project index row added | [_index.md](../../docs/example-vault/Alexandria/_index.md) — one row, regenerated (not appended) from frontmatter |
| Cross-project index updated if concept exists elsewhere | Neither concept exists in Aurora/Atlas → correctly **no** `_Concepts/` file was created (negative case). Positive case unit-tested (`test_concept_file_appears_only_at_second_project`) and demonstrated live in Task 3.4 |
| Verified by automated vault-lint | Deferred to Task 3.5 (lint doesn't exist yet); the 3.1 roadmap checkbox stays open until lint passes over this vault |

## Regression safety

`scripts/tests/test_librarian.py` (16 tests) additionally proves, byte-for-byte against the hand-built Phase 0.3 example vault: index regeneration (`Aurora`, `Atlas`), glossary parse→render round-trip, `_Concepts/Idempotency.md` regeneration, and frontmatter round-trip of every session note. Full suite: 36/36 green.

## Bug found and fixed during this task

Windows defaults `sys.stdin` to cp1252, which mis-decoded UTF-8 payload content (em-dashes became `â€”`) on the first run. `vault.py main()` now reconfigures stdin to UTF-8 before reading; the save was re-run clean.
