# Changelog

All notable changes to Alexandria will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Plugin packaging for the Claude Code marketplace: `.claude-plugin/plugin.json` manifest and `.claude-plugin/marketplace.json` catalog, so `/plugin marketplace add paynekerz/alexandria` installs the suite directly; README gained a plugin-install section. `claude plugin validate` passes in both marketplace and plugin-directory modes.
- Marketplace compliance audit (`docs/MARKETPLACE-COMPLIANCE.md`) built from the official submission docs, with tracked gaps.
- README section "What Alexandria reads, writes, and fetches" -- a plain-language disclosure of every write location, read scope, and network fetch.
- Release-checklist gates: `claude plugin validate`, single-version-source rule, and a trigger-eval drift check that voids the 7.2 extrapolation if descriptions ever change.

### Changed

- The bundled `agents/alexandria-teacher.md` now ships without a `model:` line (inherits the session model), so a plugin install works with zero writes into `~/.claude/`. Choosing a specific model at setup writes a model-pinned user-scope copy to `~/.claude/agents/alexandria-teacher.md`, which overrides the bundled agent; choosing `inherit` strips any stale pin.

### Fixed

- `setup.py --force` now re-pins or un-pins the teacher agent's model reliably (1.0.0 known issue: it could not re-fill the model line once the placeholder was consumed).

## [1.0.0] - 2026-07-18

First release. Three Claude Code skills that teach you your own codebase and archive every lesson into a dedicated Obsidian vault.

### Added

- Repository scaffold: skill folders, `agents/`, `scripts/`, `templates/`, `evals/`, `docs/`, MIT license, markdown-lint CI.
- `docs/DECISIONS.md` (15 locked decisions with rationale), `docs/VAULT-SCHEMA.md` v1 with hand-built `docs/example-vault/`, `docs/CONFIG.md`.
- First-run setup: `scripts/config.py` as the single shared config read path, `scripts/setup.py` (config + vault scaffold + teacher-agent install), Step 0 interview blocks in all three SKILL.md files; model-pinned `agents/alexandria-teacher.md` and `docs/MODEL-SELECTION.md`.
- `alexandria-teach`: core teaching workflow (SKILL.md under the 500-line budget), three-level depth system, tiered external-source rules (Tier 1 allowlist, verified-alive links only), Mermaid diagram rules, optional comprehension quiz, accuracy guardrails; manual test artifacts in `evals/manual/`.
- `alexandria-librarian`: save pipeline through `vault.py save-session` (note + glossary merge + index + cross-project `_Concepts/`, all derived files losslessly regenerable from frontmatter), `vault_lint.py` with `--repair`, `migrate.py` schema-migration scaffold with write refusal on `schemaVersion` mismatch, save flow in SKILL.md plus `references/payload.md`.
- `alexandria-recall`: `scripts/recall.py` with `search` (current-project retrieval; "you covered this in [[session]]" instead of re-teaching), `concept-check`/`cross-project` (cross-project access restricted to explicit request or exact `_Concepts/` match with announce-and-ask), and `drift` (stored commit + files vs current git state; stale sessions flagged with a refresh offer; refreshes save as new notes with `supersedes` linking their predecessor).
- 71 unit tests across `scripts/tests/`, including byte-identical index regeneration pinned against the example vault.
- Eval suite: trigger evals for all three skills (`evals/trigger/`, results in `evals/results/5.1-trigger/`; 100%/96.7%/100% positive trigger, 0% false triggers), behavior evals (`evals/behavior/`, 7 assertion-based cases over live headless sessions), token benchmark harness (`evals/benchmark/`).
- Documentation for release: root README (install, first-run walkthrough, daily-use flow, model selection, troubleshooting), `docs/WORKFLOW.md` (a narrated day of use, every step verified against the current scripts), `docs/DEMO-SCRIPT.md` (capture script for the README recording), `docs/RELEASE-CHECKLIST.md`.
- Release packaging: per-skill zips plus a full-suite zip (skills + shared `scripts/`, `agents/`, `templates/`) built with skill-creator's `package_skill.py`.

### Known issues

- On decline-path answers (asking teach about a file that doesn't exist), the mandatory save-offer footer is omitted in roughly 1 in 7 runs. Full lessons never dropped it in 21/21 measured runs. Saving still works if you ask. Details: `evals/results/5.2-behavior/SUMMARY.md`; fix tracked for a follow-up release.
- Changing `preferredModel` after first install requires editing the `model:` line in `~/.claude/agents/alexandria-teacher.md` by hand; `setup.py --force` cannot re-fill it once the placeholder is gone (see README troubleshooting).
