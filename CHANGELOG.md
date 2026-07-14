# Changelog

All notable changes to Alexandria will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Repository scaffold: skill folders, `agents/`, `scripts/`, `templates/`, `evals/`, `docs/`, MIT license, markdown-lint CI.
- Phase 0: `docs/DECISIONS.md` (15 locked decisions with rationale), `docs/VAULT-SCHEMA.md` v1 + hand-built `docs/example-vault/`, `docs/CONFIG.md`.
- Phase 1: first-run setup (`scripts/config.py` shared read path, `scripts/setup.py`, Step 0 blocks in all three SKILL.md files), `scripts/vault.py` with 19 unit tests, model-pinned `agents/alexandria-teacher.md` + `docs/MODEL-SELECTION.md`.
- Phase 2: `alexandria-teach` core workflow (125-line SKILL.md), depth system, tiered source rules, Mermaid diagram rules, optional comprehension quiz, accuracy guardrails — manual test artifacts in `evals/manual/`.
- Phase 3: `alexandria-librarian` save pipeline — `vault.py save-session` (note + glossary merge + index + cross-project `_Concepts/`; all derived files losslessly regenerable from frontmatter), `vault_lint.py` with `--repair`, `migrate.py` schema-migration scaffold with write refusal on `schemaVersion` mismatch, librarian SKILL.md save flow + `references/payload.md`; 32 new unit tests (51 total) including byte-identical regeneration pinned against the hand-built example vault.
- Phase 4: `alexandria-recall` — `scripts/recall.py` with `search` (current-project retrieval over frontmatter concepts, glossary, titles; "you covered this in [[session]]" instead of re-teaching; token cost documented in `references/token-cost.md`), `concept-check`/`cross-project` (cross-project access restricted to explicit request or exact `_Concepts/` match with announce-and-ask, negative case verified by file-access logging), and `drift` (stored commit + files vs current git state; stale sessions flagged with a refresh offer; refreshes save as new notes with `supersedes` linking their predecessor, enforced by `vault.py` and linted by `vault_lint.py`); teach's library check now routes through `recall.py search`; 20 new unit tests (71 total).
