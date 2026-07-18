# Marketplace Compliance -- Task 7.1

Requirements checklist for listing Alexandria in the Claude Code plugin ecosystem, built from the official docs fetched on **2026-07-18**. Requirements change; re-verify each source at submission time (Decision 14).

## The submission landscape (verified 2026-07-18)

The ROADMAP says "skill marketplace"; the actual distribution unit is a **plugin**. Skills ship inside a plugin, and plugins are distributed through marketplaces. Anthropic runs two public ones:

- **`claude-plugins-official`** -- curated by Anthropic at its discretion. "There is no application process, and the submission form does not add plugins to the official marketplace." ([plugins docs](https://code.claude.com/docs/en/plugins))
- **`claude-community`** ([anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community)) -- "the public community marketplace where third-party submissions land after review." This is Alexandria's target.

Community submission process ([plugins docs](https://code.claude.com/docs/en/plugins), [claude-plugins-official README](https://github.com/anthropics/claude-plugins-official)):

1. Submit via the in-app form. Individuals without a Team/Enterprise org use the **Console form: <https://platform.claude.com/plugins/submit>** (the claude.ai form requires a Team or Enterprise organization). `clau.de/plugin-directory-submission` redirects to the same docs section.
2. "Run `claude plugin validate` locally before you submit. The review pipeline runs the same check on every submission, along with automated safety screening."
3. Every listed plugin has "passed automated security scanning" and "been approved for distribution" ([claude-plugins-community README](https://github.com/anthropics/claude-plugins-community)). Detailed rubrics are not published; the official directory says only that "external plugins must meet quality and security standards for approval."
4. Approved plugins are pinned to a commit SHA in the community catalog; "CI bumps the pin automatically as you push new commits." The public catalog syncs nightly. PRs against the catalog repo are auto-closed.

Verified against the [live community catalog](https://github.com/anthropics/claude-plugins-community/blob/main/.claude-plugin/marketplace.json) on 2026-07-18: no existing plugin name contains "alexandria" (~687 entries), and `git-subdir` sources are widely used, so a `plugins/<name>/` subdirectory layout is an accepted pattern.

## Requirements checklist

Sources: [Create plugins](https://code.claude.com/docs/en/plugins), [Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces), [claude-plugins-official](https://github.com/anthropics/claude-plugins-official), [claude-plugins-community](https://github.com/anthropics/claude-plugins-community). Status: **PASS** (already satisfied), **GAP-n** (tracked fix below), **N/A**.

### Packaging format

| # | Requirement (source) | Status |
|---|---|---|
| P1 | Plugin manifest exists at `.claude-plugin/plugin.json` with `name`; only `plugin.json` lives inside `.claude-plugin/`, all component dirs at plugin root (plugins docs) | **GAP-1** |
| P2 | Skills at `<plugin root>/skills/<name>/SKILL.md` with valid YAML frontmatter incl. `description` (plugins docs) | PASS -- three skills, valid frontmatter |
| P3 | No file references escape the plugin directory; plugins are copied to a cache, `../` paths break (marketplaces docs) | PASS -- skills resolve `$SCRIPTS` as `<skill dir>/../../scripts`, which stays inside the plugin root. Exception: the teacher agent path -> **GAP-3** |
| P4 | `claude plugin validate .` exits clean; review pipeline runs the same check (plugins docs) | **GAP-2** (blocked on GAP-1) |
| P5 | Plugin `name` is kebab-case -- "the claude.ai marketplace sync rejects" other forms (marketplaces docs, validation warnings) | PASS -- `alexandria` |
| P6 | `name` is an immutable public slug; renames break installs (claude-plugins-official README) | PASS with care -- name locked at submission; availability verified 2026-07-18 |
| P7 | Skill invocation becomes namespaced `/<plugin>:<skill>` (plugins docs) | **GAP-4** -- decision needed before 7.2 |
| P8 | Distribution artifact is the git repo (SHA-pinned by the catalog), not zip bundles | PASS once GAP-1 lands -- `dist/` zips stay for manual GitHub-release installs only |

### Metadata quality

| # | Requirement (source) | Status |
|---|---|---|
| M1 | `plugin.json` carries `description`, `version`, `author`; `homepage`, `repository`, `license`, `keywords` supported and used by catalog entries (plugins docs, marketplace schema, live catalog) | **GAP-1** |
| M2 | `version` bumped every release; version resolution prefers `plugin.json`; never set it in both `plugin.json` and a marketplace entry (marketplaces docs, version-resolution warning) | **GAP-5** |
| M3 | Version consistent with CHANGELOG and git tags | PASS -- CHANGELOG `[1.0.0] - 2026-07-18`, tag `v1.0.0` pushed |
| M4 | SPDX license identifier; MIT is the friendly default (marketplace schema) | PASS -- MIT, `LICENSE` at root |
| M5 | `README.md` with installation and usage instructions (plugins docs, "Share your plugins") | PASS today for manual install; plugin-install section -> **GAP-1** |
| M6 | Public repo reachable by the review pipeline | PASS -- <https://github.com/paynekerz/alexandria>, pushed 2026-07-18 |

### Description standards

| # | Requirement (source) | Status |
|---|---|---|
| D1 | Every SKILL.md frontmatter has a `description` stating when to use the skill (plugins docs, skills authoring) | PASS -- all three, deliberately anti-ambient per Decision 15 |
| D2 | Descriptions accurate to behavior (quality review; no published rubric -- "quality and security standards" is the only official phrasing) | PASS -- backed by 5.1 trigger evals; 7.2 optimizes further |
| D3 | Plugin-level `description` for the manager UI (plugins docs) | **GAP-1** |
| D4 | Frontmatter option `disable-model-invocation: true` exists for command-only skills (plugins docs quickstart) | N/A -- deliberately not used: natural phrasing that names Alexandria ("alexandria, teach me this file") must still trigger; noted so 7.2 considers it consciously |

### Safety review of filesystem writes

The published criteria are "automated security scanning" + "automated safety screening"; no rubric is public. The defensible posture is full disclosure plus mechanical containment, which Alexandria already has -- it needs to be stated where a reviewer will look.

| # | Requirement (source) | Status |
|---|---|---|
| S1 | No hooks, no MCP servers, no LSP servers, no `bin/`, no `settings.json` defaults -- smallest reviewable surface | PASS -- skills + Python scripts only |
| S2 | All vault writes gated through `scripts/vault.py`, which refuses paths outside the vault root (unit-tested); no freehand writes | PASS -- repo invariant since 1.2 |
| S3 | Every write location outside the plugin dir disclosed in README: vault (user-chosen path), `~/.alexandria/config.json`, teacher agent file | **GAP-6** |
| S4 | Teacher-agent generation currently targets `~/.claude/agents/` -- a write into Claude Code's own config tree, and the known `setup.py --force` template-path limitation | **GAP-3** |
| S5 | Network access disclosed: Tier 1/2 source fetching (teach), link-alive verification | **GAP-6** |
| S6 | No secrets in repo; no telemetry | PASS |

### Submission logistics

| # | Requirement (source) | Status |
|---|---|---|
| L1 | Console account able to access <https://platform.claude.com/plugins/submit> (individual path) | **GAP-7** (verify at 7.3) |
| L2 | Python 3 prerequisite stated -- plugins declare no runtime dependencies | **GAP-6** |
| L3 | Own `marketplace.json` for direct `/plugin marketplace add paynekerz/alexandria` installs | Optional -- not required for community submission; decide with GAP-1 |

## Tracked gaps

Each gap is a tracked fix satisfying the 7.1 DOD. None are fixed in the 7.1 audit itself; remaining open gaps close before 7.3. Layout and naming were decided 2026-07-18 (Decision 16 in `DECISIONS.md`): repo root is the plugin root, skill folder names stay unchanged.

- [ ] **GAP-1 -- Create the plugin manifest.** Add `.claude-plugin/plugin.json` at the repo root (`name: "alexandria"`, `description`, `version: "1.0.0"`, `author`, `homepage`, `repository`, `license: "MIT"`, `keywords`). Layout decided 2026-07-18: repo root as plugin root -- the ~6.5 MB `evals/` tree rides along in user caches; accepted for zero restructuring risk. Add a plugin-install section to README. DOD: manifest committed; README covers plugin install.
- [ ] **GAP-2 -- Validation gate.** Run `claude plugin validate .` clean; add it to `docs/RELEASE-CHECKLIST.md` as a release step. DOD: validate exits 0 on the submitted layout; checklist updated. Blocked on GAP-1.
- [ ] **GAP-3 -- Make the teacher agent plugin-safe.** Ship a static `agents/alexandria-teacher.md` inside the plugin (model `inherit`) so the plugin works with zero writes into `~/.claude/`; `setup.py` model-pinning then only *offers* to write a user-scope override, and `docs/MODEL-SELECTION.md` documents both paths. Resolves S4 and the known `--force` template-path limitation. DOD: fresh plugin install teaches via the bundled agent with no `~/.claude/agents/` write; model pinning still works via the opt-in override; behavior evals unaffected.
- [x] **GAP-4 -- Namespacing decision (resolved 2026-07-18).** Skill folder names stay unchanged: marketplace installs get `/alexandria:alexandria-teach` (cosmetic stutter in the slash form only); natural-language invocation via descriptions is unaffected, manual installs keep `/alexandria-teach`, and Decision 15, the 5.1 eval strings, and all docs stay consistent as-is. Recorded as Decision 16 in `docs/DECISIONS.md`. 7.2 is unblocked.
- [ ] **GAP-5 -- Single version source.** Document in `docs/RELEASE-CHECKLIST.md`: bump `plugin.json` `version` every release, keep CHANGELOG + tag in step, never set `version` in a marketplace entry. DOD: checklist step exists; 1.0.x values consistent.
- [ ] **GAP-6 -- Safety and prerequisites disclosure.** README section enumerating: every write location (vault root -- user-chosen, refused outside by `vault.py`; `~/.alexandria/config.json`; optional agent override per GAP-3), network access (Tier 1/2 fetches + link verification, nothing else), Python 3 prerequisite. DOD: section exists and matches what the code actually does.
- [ ] **GAP-7 -- Submission access.** Confirm Console login can open <https://platform.claude.com/plugins/submit>. DOD: form reachable; executed in 7.3.

## Sources (all fetched 2026-07-18)

- <https://code.claude.com/docs/en/plugins> -- plugin structure, manifest fields, community/official marketplace split, submission forms, validate requirement, safety screening
- <https://code.claude.com/docs/en/plugin-marketplaces> -- marketplace schema, kebab-case rule, immutable names, version resolution, cache/`../` constraint, `claude plugin validate`
- <https://github.com/anthropics/claude-plugins-official> -- submission form pointer, "quality and security standards" requirement, immutable-slug warning
- <https://github.com/anthropics/claude-plugins-community> -- review criteria (official channel, automated security scanning, distribution approval), auto-closed PRs, nightly sync
- <https://github.com/anthropics/claude-plugins-community/blob/main/.claude-plugin/marketplace.json> -- name availability, entry metadata shapes, `git-subdir` precedent
