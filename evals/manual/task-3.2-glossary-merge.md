# Manual test — Task 3.2 (glossary maintenance)

Second session saved into project `Alexandria` via `vault.py save-session`, sharing the `Atomic Write` concept with the Task 3.1 session.

## Command and output

```text
$ python vault.py save-session < payload-3.2.json
note:     ...\Alexandria\Sessions\2026-07-09 session-save-pipeline.md
glossary: added Derived Data; linked Atomic Write
index:    ...\Alexandria\_index.md
concepts: none — no saved concept spans 2+ projects
exit: 0
```

## Resulting glossary entry ([_glossary.md](../../docs/example-vault/Alexandria/_glossary.md))

```markdown
## Atomic Write

Writing a file's new content to a temporary file first, then swapping it into
place in one indivisible operating-system step. A crash mid-save leaves the old
file intact instead of a half-written one. Alexandria writes every vault note
this way.

Sessions: [[2026-07-09 session-save-pipeline]], [[2026-07-09 vault-write-safety]]
```

## DOD checklist

- **One entry, two links**: exactly one `## Atomic Write` heading; its `Sessions:` line links both notes.
- **Definition never duplicated or rewritten**: the 3.2 payload deliberately carried a *different* wording for `Atomic Write`; the script ignored it and kept the 3.1 definition verbatim (also unit-tested: `test_second_session_appends_glossary_link_not_definition`).
- **New concept added at intro level**: `Derived Data` entry created, alphabetically placed.
- **Obsidian graph view shows the links**: requires owner to open `docs/example-vault/` in Obsidian — pending, checkbox stays open until confirmed.
