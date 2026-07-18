# Alexandria -- Decision Record

These decisions were locked during planning. Don't relitigate them mid-build. Changing one requires updating both this file and the Locked Decisions table in the internal build plan, in the same commit.

## 1. Runtime: Claude Code only (v1)

**Choice:** Alexandria v1 runs exclusively in Claude Code. Filesystem access is required for the vault.

**Rationale:** Every core behavior needs direct filesystem and shell access: writing session notes, maintaining glossaries and indexes, reading git state for drift detection, running deterministic scripts. Claude Code provides all of it natively; claude.ai and the desktop app don't (a filesystem-MCP path for desktop is a Phase 8 stretch investigation, not a v1 target). Building for one runtime keeps v1 testable and honest instead of shipping a degraded mode we can't verify.

## 2. Architecture: suite of three skills

**Choice:** Three separate skills -- `alexandria-teach`, `alexandria-librarian`, `alexandria-recall` -- rather than one monolithic skill.

**Rationale:** The three jobs have different triggers, different context needs, and different failure modes. Teaching needs the code in context; saving needs only the finished lesson and the vault scripts; recall needs the vault index but not the code. Splitting them keeps each SKILL.md small (token efficiency, Axiom 2) and each loads only when its job is actually happening, instead of one skill dragging teaching prose, save mechanics, and retrieval rules into every invocation.

## 3. Vault: new dedicated Obsidian vault, user-chosen path

**Choice:** Lessons live in a dedicated Obsidian vault at a user-chosen path, defaulting to `~/Desktop/Alexandria`.

**Rationale:** A dedicated vault keeps Alexandria's automated writes out of any existing personal vault; the librarian can regenerate indexes and append to glossaries without risking your own notes. Obsidian gives wiki-links, graph view, and native Mermaid rendering for free, and the schema leans on all three. The path is user-chosen because people organize their machines differently; the default is visible (Desktop) so a first-time user can find what was just created.

## 4. Vault layout: folder per project, per-project glossary and index, one note per session

**Choice:** `Vault/<Project>/` per project, containing `_glossary.md`, `_index.md`, and `Sessions/` with one note per session.

**Rationale:** Project folders make the default retrieval scope (current project only) a filesystem boundary rather than a convention. One note per session keeps notes small and stampable with a single commit hash, so drift detection works per-lesson. The underscore-prefixed glossary and index sort to the top of each folder and are cheap for scripts to regenerate, since they derive entirely from session frontmatter.

## 5. Session unit: one question -> one answer, save offered every time

**Choice:** A session is one question and one answer. Every teach response ends with a save offer; saving happens only when the user asks.

**Rationale:** Small session units produce notes that are individually linkable, individually quizzable, and individually staleness-checkable. Offering the save at the end of every response makes persistence a habit without making it automatic; automatic saves would fill the vault with half-lessons and noise you never asked to keep. You stay the curator of your own library.

## 6. Concept granularity: domain/architectural concepts, user-confirmed

**Choice:** Concepts are the domain and architectural ideas required to understand the system (for an Unreal multiplayer system: replication, authority, RPCs, relevancy) -- not variable names or trivia. The user confirms the concept list before save.

**Rationale:** Concepts are the unit of cross-linking, glossary entries, and cross-project indexing, so they must be things worth finding again in six months. Variable names and file trivia would pollute the glossary and make the graph view useless. User confirmation before save is the quality gate: the vault only ever contains concepts you agreed were real.

## 7. External sources: tiered allowlist first, open web as fallback

**Choice:** Tier 1 allowlist (MIT OCW, Harvard PLL, Stanford Online, official framework/language docs, LeetCode for algorithms and data structures, curated YouTube channels) searched first; Tier 2 open web only when Tier 1 has nothing; every link verified alive before inclusion.

**Rationale:** A vault full of dead or low-quality links is worse than no links. The Tier 1 list is stable, free, and reputable, which makes verification cheap and the archived material durable. Tier 2 stays available so niche concepts aren't left uncovered, but only as a documented fallback. Verifying every link before it enters a note enforces Axiom 3 at the exact boundary where hallucinated URLs would otherwise slip in.

## 8. Diagrams: Mermaid only

**Choice:** All diagrams are Mermaid.

**Rationale:** Obsidian renders Mermaid natively: no plugins, no image files, no external renderer. Diagrams stay text, which means they diff in git, survive vault moves, and cost nothing to store. Accepting one syntax also means one set of Obsidian-safe syntax constraints instead of QA-ing multiple formats. **Limitation:** Mermaid can't express everything (complex UML, precise layout control); when Mermaid can't say it cleanly, the answer is prose, not another diagram tool.

## 9. Depth: per-session flag -- intro / practitioner / deep-dive

**Choice:** Each session has a depth level: `intro` (default, assumes no prior knowledge), `practitioner`, or `deep-dive`. Default comes from config; any session can override it.

**Rationale:** One explanation depth can't serve both a non-technical founder and a senior engineer reading the same file. Three named levels are enough to be meaningfully different and few enough to define precisely (vocabulary, assumed background, whether fundamentals get re-derived). `intro` as the shipping default honors Axiom 1: assume no prior knowledge unless told otherwise. Depth is stamped in frontmatter so recall knows what level a past lesson was pitched at.

## 10. Drift detection: commit hash + file paths on every session

**Choice:** Every session note records the git commit hash and the file paths it explained. Recall compares those against current git state and flags stale explanations.

**Rationale:** Code moves; explanations don't. Without staleness tracking the vault silently rots into a library of confident, outdated lessons -- a direct Axiom 3 violation. Commit hash plus file list is the cheapest signal that is still precise: no content hashing, no embeddings, just "have the files this lesson covered changed since it was written?" Refreshed lessons link their predecessor rather than overwriting it, preserving the learning history.

## 11. Comprehension checks: optional 2-3 question quiz

**Choice:** An optional quiz (2-3 questions) at session end, controlled by a config flag with per-session override. Results are saved into the session note.

**Rationale:** Retrieval practice is the best-evidenced way to make a lesson stick, but forcing a quiz on someone who wanted a quick answer would make the whole suite feel like homework -- so it's opt-in and skippable per session. Two to three questions scoped to the session's confirmed concepts keeps it honest (nothing untaught gets tested) and cheap. Storing results in frontmatter gives Phase 8's spaced-repetition export real data to build on.

## 12. Model selection: config preference + pinned subagent

**Choice:** Model preference is stored in config and enforced through a model-pinned `alexandria-teacher` subagent in Claude Code. Otherwise the skill can only recommend `/model` at session start.

**Rationale:** **Hard limitation, stated plainly: a Claude Code skill cannot switch the running model. Ever.** Skills are instructions loaded into whatever model is already running; they have no API to change it. The one real enforcement mechanism Claude Code offers is subagents, whose frontmatter can pin a model -- so the heavy explanation work is delegated to `alexandria-teacher`, generated at setup with the user's chosen model. Anywhere the subagent isn't in play, the preference is a recommendation to run `/model` and nothing more, and the docs say so rather than pretending otherwise.

## 13. Metadata: YAML frontmatter schema, versioned from day one

**Choice:** Every note carries a YAML frontmatter schema; the vault carries a `schemaVersion` starting at 1.

**Rationale:** Frontmatter is what makes the vault a database instead of a pile of prose: indexes regenerate from it, recall queries it, lint validates against it. Versioning from day one costs one integer field now and buys a safe migration path later; retrofitting versioning onto thousands of unversioned notes is the kind of pain that kills side projects. The librarian refuses writes on a version mismatch instead of guessing.

## 14. Distribution: GitHub first, marketplace second

**Choice:** Ship v1 as a GitHub repo with manual install; pursue skill marketplace listing afterward.

**Rationale:** A GitHub release is entirely under our control and unblocks real users (and real feedback) the day v1 works. Marketplace submission adds external review, packaging requirements, and timelines we don't control -- worth doing (Phase 7), but as a second step, verified against current submission requirements at submission time rather than assumptions made months earlier.

## 15. Invocation: explicit only

**Choice:** Skills trigger on explicit invocation only. Descriptions are deliberately written to avoid ambient triggering.

**Rationale:** Alexandria's skills read vaults, fetch external sources, and write files -- none of which should happen because a description loosely pattern-matched an ordinary coding request. A user asking "fix this bug" must never get a surprise lesson or a surprise vault write. Explicit invocation keeps the suite predictable and is enforced by eval: the Phase 5 trigger evals test false-trigger rates, not just trigger rates.

## 16. Plugin packaging: repo root as plugin root, skill names unchanged

**Choice** (2026-07-18, for marketplace distribution): the repo root is the plugin root -- `.claude-plugin/plugin.json` sits at the top of this repository with `skills/`, `scripts/`, `agents/`, and `templates/` in place. Skill folder names stay `alexandria-teach`, `alexandria-librarian`, `alexandria-recall`, so plugin installs expose `/alexandria:alexandria-teach` while manual installs keep `/alexandria-teach`.

**Rationale:** Restructuring into a `plugins/` subdirectory right after v1.0.0 would touch install docs, eval runner paths, and packaging scripts for a cosmetic win; the cost of the root layout is that the `evals/` tree (~6.5 MB) is copied into each user's plugin cache, which we accept. Renaming skill folders to get the cleaner `/alexandria:teach` would leak generic bare names (`/teach`, `/recall`) into manual installs -- directly against Decision 15 -- and would invalidate the Phase 5 eval strings the descriptions are pinned to. The stutter affects only the slash form on one install path; the documented natural-language invocation ("alexandria, teach me this file") triggers off descriptions and is identical everywhere. Full audit: `docs/MARKETPLACE-COMPLIANCE.md` (GAP-1, GAP-4).
