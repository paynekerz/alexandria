---
name: alexandria-recall
description: Memory layer of the Alexandria learning suite. Use ONLY when the user explicitly asks Alexandria what it has already taught them or whether a lesson is stale (e.g. "alexandria, have we covered this before?"). Never use for general search, documentation lookup, or memory requests that don't name Alexandria.
---

# alexandria-recall

You are Alexandria's memory. Full retrieval and drift detection land in Phase 4 (see the internal build plan); until then this skill only performs setup.

## Step 0 — Config check (every invocation, before anything else)

Let `SCRIPTS` = this skill's directory `/../../scripts` (the repo's shared scripts folder).

Run `python "$SCRIPTS/config.py"` and branch on the exit code:

- **0** — stdout is the validated config JSON. Use it for this session. Continue to Step 1.
- **1** — no config: this is a first run. Do the interview below, then continue to Step 1.
- **2** — config invalid: report the exact field error from stderr and offer to re-run setup with `--force`. Do not guess or substitute values (Axiom 3).

### First-run interview (exit code 1 only)

Tell the user this is Alexandria's one-time setup, then ask all four questions in a single AskUserQuestion call:

1. **Vault location** — where the Obsidian library lives. Default (recommended): `~/Desktop/Alexandria`.
2. **Teaching model** — model for explanation work. Options: `sonnet` (recommended), `opus`, `haiku`, `inherit` (whatever the session runs).
3. **Default lesson depth** — `intro` (recommended; assumes no prior knowledge), `practitioner`, `deep-dive`.
4. **End-of-lesson quiz** — `off` (recommended) or `on`: 2–3 optional comprehension questions after each lesson.

Then run:

```bash
python "$SCRIPTS/setup.py" --vault-path "<answer>" --model "<answer>" --depth <answer> --quiz <on|off>
```

On exit 0, tell the user in one short paragraph what was created (config path, vault path) and that the vault opens in Obsidian. On any other exit code, show the script's error verbatim and stop.

**Then immediately continue with the user's original request in this same turn.** Setup is a detour, never the destination — if the user asked whether something was covered before, answer that now. Never end the turn after setup.

## Step 1 — Recall

Not yet implemented (Phase 4.1). Tell the user retrieval isn't built yet and point them to the internal build plan Phase 4.
