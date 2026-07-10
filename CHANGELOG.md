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
