# Alexandria Vault Schema -- v1

This document is the frozen v1 specification for everything Alexandria writes into a vault. All vault writes go through `scripts/vault.py` and must conform to this schema. Changing anything here after v1 freeze requires a `schemaVersion` bump and a migration.

A hand-built example vault conforming to this spec lives in [example-vault/](example-vault/); open it as a vault in Obsidian to see every file type rendered.

## 1. Vault root layout

```text
<vault root>/                      user-chosen; default ~/Desktop/Alexandria
├── .alexandria/
│   └── meta.json                  vault metadata; carries schemaVersion
├── Welcome.md                     written once at vault creation
├── _Concepts/                     cross-project concept files (see §7)
│   └── <Concept>.md               exists ONLY for concepts taught in ≥ 2 projects
└── <Project>/                     one folder per project
    ├── _index.md                  chronological session table (see §6)
    ├── _glossary.md               concept definitions for this project (see §5)
    └── Sessions/
        └── YYYY-MM-DD <slug>.md   one note per session (see §4)
```

Rules:

- Obsidian ignores dot-folders, so `.alexandria/` never appears in the vault UI; it is machine metadata only.
- `<Project>` folder names are the project identifier. They must match the `project` frontmatter field of every session inside them, exactly.
- `_Concepts/` exists at the root from vault creation (empty until a concept reaches a second project).
- Nothing outside this layout is ever written. `scripts/vault.py` enforces this.

## 2. Naming conventions

| Thing | Rule | Example |
|---|---|---|
| Project folder | As given by user/repo name; no leading `_` or `.` | `Aurora` |
| Session file | `YYYY-MM-DD <slug>.md`: date + kebab-case slug of the title | `2026-06-12 checkout-tokenization-flow.md` |
| Concept name | Canonical Title Case string; identical everywhere it appears (frontmatter, glossary heading, `_Concepts/` filename) | `Idempotency` |
| Cross-project concept file | `_Concepts/<Concept>.md` | `_Concepts/Idempotency.md` |

Slugs and concept names must avoid characters Obsidian or Windows reject in filenames: `\ / : * ? " < > | # ^ [ ]`.

Because session filenames start with an ISO date and a project-specific slug, they are unique vault-wide in practice, so bare wiki-links to sessions (`[[2026-06-12 checkout-tokenization-flow]]`) resolve unambiguously. Links to glossary entries must always be path-qualified (see section 5) because every project has a file named `_glossary.md`.

## 3. Session note frontmatter -- field reference

Every session note starts with YAML frontmatter containing exactly these fields:

| Field | Type | Required | Meaning / constraints |
|---|---|---|---|
| `project` | string | required | Must equal the containing project folder name exactly |
| `title` | string | required | Human-readable lesson title; the filename slug derives from it |
| `date` | string | required | Session date, ISO 8601 `YYYY-MM-DD` |
| `depth` | string | required | One of `intro`, `practitioner`, `deep-dive` |
| `concepts` | string[] | required, >= 1 entry | Canonical concept names taught or referenced this session; each must have a `_glossary.md` entry in this project |
| `files` | string[] | required, may be empty | Repo-relative paths of the files this lesson explained (empty for pure-concept lessons) |
| `commit` | string | required | Git commit hash (short or full) of the repo at teach time; the literal string `unversioned` when the project is not a git repository |
| `sources` | string[] | required, may be empty | External URLs cited in this note; every entry was verified alive at write time (see `references/sources.md`) |
| `quizScore` | string | optional | `"<correct>/<asked>"`, e.g. `"3/3"`; present only when a comprehension quiz ran |
| `supersedes` | string | optional | Filename (no extension) of the session this note refreshes after drift; present only on refresh notes |
| `schemaVersion` | integer | required | Always `1` for this schema |

Unknown fields are a lint error. Field order is fixed as listed above so notes diff cleanly.

## 4. Session note -- worked example

Filename: `Aurora/Sessions/2026-06-12 checkout-tokenization-flow.md`

```markdown
---
project: Aurora
title: How checkout tokenization works
date: 2026-06-12
depth: intro
concepts:
  - Tokenization
  - PCI Scope
  - Idempotency
files:
  - src/Checkout/TokenizeHandler.php
  - src/Api/GatewayClient.php
commit: a1b2c3d
sources:
  - https://developer.mozilla.org/en-US/docs/Glossary/Idempotent
schemaVersion: 1
---

# How checkout tokenization works

## Lesson

Explanation prose. The first mention of each concept links to this
project's glossary entry: [[Aurora/_glossary#Tokenization|tokenization]].

## Files

- `src/Checkout/TokenizeHandler.php` @ `a1b2c3d`

## Sources

- [Idempotent — MDN Glossary](https://developer.mozilla.org/en-US/docs/Glossary/Idempotent)

## Comprehension

Quiz results table (only when a quiz ran).
```

Body structure: one `# <title>` heading, then `## Lesson` (required), `## Files` (required when `files` is non-empty), `## Sources` (required when `sources` is non-empty), `## Comprehension` (required when `quizScore` is present). No other top-level sections.

Linking rules inside the body:

- First mention of a concept -> glossary link: `[[<Project>/_glossary#<Concept>|<display text>]]`
- Reference to a prior session -> bare session link: `[[2026-06-12 checkout-tokenization-flow]]`
- External URLs appear only under `## Sources` and must also be listed in `sources` frontmatter.

## 5. `_glossary.md` -- worked example

One per project folder. One `##` entry per concept, alphabetized. The heading text is the canonical concept name; glossary links (`[[<Project>/_glossary#<Concept>]]`) depend on it matching exactly. Definitions are always written at intro level regardless of the sessions' depth. New sessions using an existing concept append a session link; they never duplicate or rewrite the definition.

```markdown
---
project: Aurora
schemaVersion: 1
---

# Glossary — Aurora

## Idempotency

An operation is idempotent when doing it once and doing it several
times produce the same result...

Sessions: [[2026-06-12 checkout-tokenization-flow]], [[2026-06-19 webhook-handling]]

## Tokenization

Swapping a real card number for a meaningless stand-in token...

Sessions: [[2026-06-12 checkout-tokenization-flow]]
```

## 6. `_index.md` -- worked example

One per project folder: a chronological table of every session, newest first. It is entirely derived data, regenerable losslessly from session frontmatter alone (`scripts/vault_lint.py --repair`). Hand edits are forbidden; they will be overwritten.

```markdown
---
project: Aurora
schemaVersion: 1
---

# Index — Aurora

| Date | Session | Depth | Concepts | Files | Commit |
|---|---|---|---|---|---|
| 2026-06-19 | [[2026-06-19 webhook-handling]] | intro | Webhooks, HMAC Verification, Idempotency | src/Webhook/Listener.php | e4f5a6b |
| 2026-06-12 | [[2026-06-12 checkout-tokenization-flow]] | intro | Tokenization, PCI Scope, Idempotency | src/Checkout/TokenizeHandler.php, src/Api/GatewayClient.php | a1b2c3d |
```

Column contents come 1:1 from frontmatter: `date`, wiki-link to the note, `depth`, `concepts` comma-joined, `files` comma-joined, `commit`.

## 7. Cross-project concept file -- worked example

`_Concepts/<Concept>.md` is created by the librarian **only** when a concept appears in a second project; single-project concepts never get one. It links every project's glossary entry and every session using the concept, plus the reference material already gathered.

Filename: `_Concepts/Idempotency.md`

```markdown
---
concept: Idempotency
projects:
  - Aurora
  - Atlas
schemaVersion: 1
---

# Idempotency

Taught in 2 projects.

## Aurora

Glossary: [[Aurora/_glossary#Idempotency|Idempotency in Aurora]]

- [[2026-06-12 checkout-tokenization-flow]]
- [[2026-06-19 webhook-handling]]

## Atlas

Glossary: [[Atlas/_glossary#Idempotency|Idempotency in Atlas]]

- [[2026-06-25 retry-idempotency]]

## References

- [Idempotent — MDN Glossary](https://developer.mozilla.org/en-US/docs/Glossary/Idempotent)
```

Frontmatter fields: `concept` (string, required, equals filename and canonical name), `projects` (string[], required, >= 2 entries, folder names), `schemaVersion` (integer, required).

## 8. `.alexandria/meta.json` -- worked example

Machine-read vault metadata. The librarian checks `schemaVersion` here before any write and refuses on mismatch.

```json
{
  "schemaVersion": 1,
  "createdAt": "2026-06-12T14:03:00-05:00",
  "generator": "alexandria",
  "generatorVersion": "0.1.0"
}
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schemaVersion` | integer | required | Vault-wide schema version; `1` |
| `createdAt` | string | required | ISO 8601 timestamp of vault creation |
| `generator` | string | required | Always `"alexandria"` |
| `generatorVersion` | string | required | Alexandria version that created the vault |

## 9. Invariants (what lint enforces)

1. Every session note's frontmatter validates against section 3: types, required fields, allowed `depth` values, no unknown fields.
2. `project` field == containing folder name; file lives under `Sessions/`.
3. Every concept in any session's `concepts` has a matching `##` heading in that project's `_glossary.md`, and that glossary entry links back to the session.
4. `_index.md` content is byte-identical to what regeneration from frontmatter produces.
5. Every wiki-link in the vault resolves to an existing file/heading.
6. A `_Concepts/<Concept>.md` file exists **iff** that concept appears in >= 2 projects' glossaries, and it links all of them.
7. `sources` URLs appear in the note body's `## Sources` section and nowhere else.
8. `.alexandria/meta.json` exists, parses, and `schemaVersion` matches what the tooling expects.
