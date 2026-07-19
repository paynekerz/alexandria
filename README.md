# Alexandria

Alexandria is a suite of three Claude Code skills that teaches you your own codebase like a patient instructor, then archives every lesson into a personal Obsidian library. Ask it to teach you a file; it explains at the depth you choose, offers to save the lesson, and files it with a glossary, a project index, and a git commit stamp. Next time you ask about the same topic, it links the old lesson instead of re-teaching it -- and flags it if the code has changed since.

You end up with a library that grows one lesson at a time: per-project glossaries, cross-project concept indexes, and drift detection that tells you when an explanation has gone stale.

## The three skills

| Skill | Job | You invoke it when |
|---|---|---|
| `alexandria-teach` | Explains code at your chosen depth (`intro`, `practitioner`, `deep-dive`) | "alexandria, teach me this file" |
| `alexandria-librarian` | Saves finished lessons into the vault; maintains glossaries and indexes | "save" (accepting teach's save offer) |
| `alexandria-recall` | Surfaces past lessons before anything gets re-taught; flags stale ones | "alexandria, have we covered this before?" |

They only run when you name Alexandria or use the slash command (`/alexandria-teach`, etc.). Asking Claude Code to "fix this bug" will never trigger a surprise lesson or a vault write; that's by design.

## Requirements

- **Claude Code** (CLI or desktop). Alexandria v1 runs only in Claude Code -- it needs filesystem access for the vault.
- **Python 3.9+** on your PATH as `python`. The scripts use only the standard library; there's nothing to `pip install`.
- **Obsidian** (free) to read your library. Optional -- the vault is plain Markdown -- but wiki-links, graph view, and Mermaid diagrams render there.
- **git** on your PATH if you want drift detection. Projects without git still work; their lessons are stamped `unversioned`.

## Install

### Option A -- as a plugin (recommended)

Inside Claude Code:

```shell
/plugin marketplace add paynekerz/alexandria
/plugin install alexandria@alexandria
```

That's the whole install. Skills arrive namespaced (`/alexandria:alexandria-teach`), though you'll normally just talk to them by name ("alexandria, teach me this file"). Once the suite is listed in Anthropic's community marketplace you can install from there instead: `/plugin marketplace add anthropics/claude-plugins-community`, then `/plugin install alexandria@claude-community`.

### Option B -- manual copy

Alexandria installs as three skill folders plus a shared `scripts/`, `agents/`, and `templates/` folder that must sit beside them under your `.claude` directory. The skills locate the scripts relative to their own path, so the layout matters.

1. Clone the repo:

   ```bash
   git clone https://github.com/paynekerz/alexandria.git
   ```

2. Copy the three skill folders into your skills directory:

   ```bash
   cp -r alexandria/skills/alexandria-teach alexandria/skills/alexandria-librarian alexandria/skills/alexandria-recall ~/.claude/skills/
   ```

3. Copy the shared folders next to them:

   ```bash
   cp -r alexandria/scripts alexandria/agents alexandria/templates ~/.claude/
   ```

   On Windows (PowerShell), replace `~/.claude` with `$env:USERPROFILE\.claude` and use `Copy-Item -Recurse`.

**Success condition:** `~/.claude/skills/` contains the three `alexandria-*` folders, and `~/.claude/scripts/config.py` exists. Restart Claude Code so it picks up the new skills.

## First-run setup

You don't run a setup command. The first time you invoke any Alexandria skill, it notices there's no config and walks you through a one-time interview -- four questions:

1. **Vault location** -- where your library lives. Default: `~/Desktop/Alexandria`. Pick anywhere writable; a dedicated folder is created for you, so it never touches an existing Obsidian vault.
2. **Teaching model** -- which Claude model does the heavy explanation work. `sonnet` is the recommended default. (See "Choosing a model" below for what this can and can't control.)
3. **Default lesson depth** -- `intro` assumes no prior knowledge and is the default. You can override depth per session, so this is only what you get when you don't ask.
4. **Quiz on or off** -- an optional 2-3 question comprehension check at the end of each lesson. Off by default; you can say "quiz me" in any session regardless.

Setup then writes `~/.alexandria/config.json`, scaffolds the empty vault (a `Welcome.md`, a `_Concepts/` folder, and vault metadata), pins the teacher subagent if you chose a specific model, and continues with whatever you originally asked. The second invocation skips all of this.

**Note:** the vault opens directly in Obsidian -- File > Open folder as vault > pick your vault path.

## Daily use

A full loop looks like this:

1. **Learn.** In any project, ask: `alexandria, teach me src/webhooks.php`. Teach reads the code (never guesses from memory), checks your library for concepts you've already covered, and explains at your depth. Already-taught concepts arrive as `[[wiki-links]]` to your own glossary instead of re-explanations.
2. **Save.** Every lesson ends with a save offer. Say "save" and the librarian confirms the concept list with you first -- you curate what's worth keeping -- then files the note into `Vault/<Project>/Sessions/`, updates the project glossary and index, and stamps it with the current git commit.
3. **Recall.** Days later, ask: `alexandria, have we covered webhook verification before?`. Recall searches this project's library and answers "you covered this in [[2026-07-02 webhook-handling]]" with a link, plus what that lesson *didn't* cover. It never re-explains what a linked note already teaches.
4. **Drift.** If the files a lesson explained have changed since it was saved, recall flags it: "this explanation predates changes to `src/webhooks.php` -- want a refreshed lesson?" A refresh is saved as a new note linked to its predecessor; your learning history is never overwritten.

Everything is scoped to the current project by default. Lessons from your other projects are pulled in only when you explicitly ask, or when Alexandria spots an exact concept match in the cross-project index -- and it asks permission first either way.

A narrated day of real use is in [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Choosing a model

Plainly: **a Claude Code skill cannot switch the model your session runs on.** Any skill that claims otherwise is overstating what skills can do.

What Alexandria does instead: the heavy explanation work is delegated to a subagent (`alexandria-teacher`), and subagents are the one mechanism Claude Code provides for pinning a model. The bundled agent inherits your session's model; if you choose a specific model at setup, a pinned copy is written to `~/.claude/agents/alexandria-teacher.md` (user-scope agents override the bundled one), so lessons genuinely run on the model you picked -- even if your session is running something else. The conversational parts (scoping your question, the save offer) still run on your session's model, and there Alexandria can only *recommend* you run `/model`.

Full explanation: [docs/MODEL-SELECTION.md](docs/MODEL-SELECTION.md). To change your choice later, re-run `setup.py --force` with the new model (see Troubleshooting).

## The vault

The vault is plain Markdown with YAML frontmatter -- readable without Alexandria, portable, and diffable. Every session note records the project, depth, concepts, files explained, git commit, and any verified external sources. Indexes and glossaries are derived entirely from note frontmatter, so `scripts/vault_lint.py --repair` can rebuild them losslessly if anything drifts.

The full v1 schema -- layout, naming rules, frontmatter fields, glossary and index formats -- is frozen in [docs/VAULT-SCHEMA.md](docs/VAULT-SCHEMA.md). A hand-built example vault you can open in Obsidian is at [docs/example-vault/](docs/example-vault/).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Skill says config is invalid and names a field | `~/.alexandria/config.json` was hand-edited into a bad state. Fix the named field, or re-run setup: `python ~/.claude/scripts/setup.py --force ...` (it will tell you the flags it needs). |
| "vault schemaVersion mismatch" and the skill refuses to write | Your vault was created by a different Alexandria version. Don't edit `meta.json` by hand; run `python ~/.claude/scripts/migrate.py` and follow its instructions. |
| Retrieval fails naming a broken note | A session note has invalid frontmatter (usually from hand-editing). Run `python ~/.claude/scripts/vault_lint.py` to see every problem, and `--repair` to regenerate the derived files. Lint never touches your lesson prose. |
| Teacher subagent not found | Plugin install: run `/plugin` and check `alexandria` is enabled, then `/reload-plugins`. Manual install: `~/.claude/agents/alexandria-teacher.md` is missing -- re-run step 3 of Install. |
| Changed `preferredModel` but lessons still use the old model | Re-run setup with the new choice: `python <path>/scripts/setup.py --force --model <choice> --vault-path <your vault>`. It re-pins (or un-pins, for `inherit`) `~/.claude/agents/alexandria-teacher.md` and updates the config together. |
| A teach response is missing the save-offer footer | Rare known issue (tracked). The save still works -- just say "alexandria, save this lesson". |
| `python` not found | Install Python 3.9+ and make sure it's on PATH as `python` (on macOS you may need `alias python=python3` or adjust the commands). |
| Skills don't appear after install | Restart Claude Code; skills are discovered at startup. Then check the Success condition under Install. |

## What Alexandria reads, writes, and fetches

Stated plainly so you can decide whether to trust it:

**Writes.** Exactly three locations, nothing else:

- **Your vault** (the path you chose at setup; default `~/Desktop/Alexandria`). Every write goes through `scripts/vault.py`, which validates the target and refuses any path outside the vault root -- this is unit-tested, not a convention. Nothing is ever saved without you saying "save", and you confirm the concept list first.
- **`~/.alexandria/config.json`** -- your setup answers. Written once at first run, again only on `setup.py --force`.
- **`~/.claude/agents/alexandria-teacher.md`** -- only if you choose a specific teaching model at setup (the pinned subagent copy; see "Choosing a model"). Choosing `inherit` writes nothing here.

**Reads.** The code you ask to be taught, your vault, and your project's git state (`git log`, `rev-parse`) for drift stamps. Recall reads only the current project's vault folder unless you explicitly ask for cross-project material.

**Fetches.** External sources are conditional: only when a concept genuinely benefits, from a tiered allowlist first (MIT OCW, official docs, etc.), and every link is fetched to verify it's alive before it enters a note. A plain code walkthrough fetches nothing. There is no telemetry, no analytics, and no network traffic besides those source fetches.

**Runs.** Python 3.9+ standard library only -- no pip installs, no third-party packages, no hooks, no MCP servers.

## Project documents

- [docs/DECISIONS.md](docs/DECISIONS.md) -- the decision record: every locked design decision with its rationale
- [docs/VAULT-SCHEMA.md](docs/VAULT-SCHEMA.md) -- the frozen v1 vault schema
- [docs/CONFIG.md](docs/CONFIG.md) -- config file reference (`~/.alexandria/config.json`)
- [docs/MODEL-SELECTION.md](docs/MODEL-SELECTION.md) -- how your model choice is honored, and its limits
- [docs/WORKFLOW.md](docs/WORKFLOW.md) -- a narrated day of real use
- [CHANGELOG.md](CHANGELOG.md)

## License

[MIT](LICENSE)
