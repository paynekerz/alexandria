# Manual test — Task 3.4 (cross-project concept index)

Three saves through `vault.py save-session` into a scratch **copy** of `docs/example-vault/` (so the committed example vault stays untouched), tracking `_Concepts/` after each. Concept under test: `Rate Limiting`, new to both projects. The stage-2 source URL was fetched and confirmed alive before inclusion (MDN Glossary "Rate limit").

## Lifecycle

| Stage | Save | `_Concepts/` afterward |
|---|---|---|
| 0 | — | `Idempotency.md` only |
| 1 | `Rate Limiting` in **Aurora** (project A) | unchanged — single-project concept, **no file created** |
| 2 | `Rate Limiting` in **Atlas** (project B) | `Rate Limiting.md` **appears**, stdout: `concepts: ...\_Concepts\Rate Limiting.md` |
| 3 | third session, back in **Aurora** | `Rate Limiting.md` **updated** — new session listed under Aurora |

## Final `_Concepts/Rate Limiting.md`

```markdown
---
concept: Rate Limiting
projects:
  - Aurora
  - Atlas
schemaVersion: 1
---

# Rate Limiting

Taught in 2 projects.

## Aurora

Glossary: [[Aurora/_glossary#Rate Limiting|Rate Limiting in Aurora]]

- [[2026-07-09 api-throttling]]
- [[2026-07-11 handling-429s]]

## Atlas

Glossary: [[Atlas/_glossary#Rate Limiting|Rate Limiting in Atlas]]

- [[2026-07-10 queue-rate-limits]]

## References

- [Rate limit — MDN Glossary](https://developer.mozilla.org/en-US/docs/Glossary/Rate_limit)
```

## DOD checklist

- **Created only at the second project**: stage 1 produced no file; stage 2 did. Also pinned as unit test (`test_concept_file_appears_only_at_second_project`) plus the schema-invariant test that `_Concepts/` contents equal exactly the set of ≥2-project concepts (`test_single_project_concepts_get_no_file`).
- **Links every project glossary entry and every session**: both `Glossary:` links present; all three sessions listed, per-project, date-ascending.
- **Reference material gathered**: the verified MDN link from the Atlas session landed under `## References`, deduplicated by URL across sessions (the file regenerates deterministically from frontmatter + note `## Sources` sections — `render_concept_file` reproduces the hand-written `_Concepts/Idempotency.md` byte-for-byte, unit-tested).
- Projects ordered by first-taught date; `Taught in N projects.` count updates as projects join.
