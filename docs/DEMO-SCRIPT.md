# Demo recording script

Shot-by-shot script for the README's terminal recording. It captures the [WORKFLOW.md](WORKFLOW.md) narrative compressed to ~90 seconds. Record it once, convert to GIF, embed in the README.

## Prerequisites

- **Record inside WSL.** asciinema needs a Unix pty; it does not run in PowerShell or Git Bash. `sudo apt install asciinema` (or `pipx install asciinema`). Claude Code and the Alexandria scripts work fine from WSL as long as `python3` and `git` are present.
- A throwaway sample repo. Reuse the verified one: copy `evals/behavior/fixture-shop` somewhere as `sample-shop`, `git init`, commit.
- A scratch config so your real library is untouched: `export ALEXANDRIA_CONFIG_DIR=~/demo-alexandria-config` and `export ALEXANDRIA_AGENTS_DIR=~/demo-alexandria-agents` in the recording shell. Delete both dirs plus the demo vault afterward.
- Terminal at 100x28, a quiet prompt (no powerline segments), font >= 14pt -- it becomes a GIF; small text dies.

## Scenes

Type naturally, don't paste. Pause ~1s where marked so the GIF breathes.

1. **Title beat.** `cd ~/demo/sample-shop`, then `ls src/` -- shows `verify.php webhook.php`. Pause.
2. **First invocation.** Start `claude`, type: `alexandria, teach me src/verify.php`. Let the first-run interview render, take the defaults on camera (this is the setup walkthrough in one shot). Wait for setup's summary lines (config path, vault root, teacher agent).
3. **The lesson.** Let the intro-depth lesson stream. Don't scroll back. Wait until the save-offer block is fully visible -- that block is the money shot; hold on it ~2s.
4. **Save.** Type `save`. Confirm the concept list when asked. Wait for the librarian's report (note path, `glossary: added ...`, index). Pause.
5. **Recall.** Type: `alexandria, have we covered webhook signatures before?` Wait for the `You covered this in [[...]]` line. Pause ~2s.
6. **Drift.** Exit claude. In the shell: append a comment to `src/verify.php`, `git commit -am "verify: timestamp skew tolerance"`. Restart claude, ask the same recall question. Wait for the stale flag: "predates changes to src/verify.php -- want a refreshed lesson?" Hold ~2s. (Decline the refresh; the flag is the point, and it keeps the recording short.)
7. **Closer.** Exit claude. Run `ls ~/demo/Alexandria/sample-shop/Sessions/` showing the saved note, then `python3 ~/.claude/scripts/vault_lint.py` -> `clean: 0 findings`. End.

**Note:** scenes 2-6 are live model output; length and wording will vary between takes. If a take drags past ~2 minutes, re-record the slow scene rather than speeding up the cast so far it looks fake. If teach omits the save-offer block on a decline-path answer (rare known flake), just re-take the scene.

## Record, convert, embed

```bash
asciinema rec demo.cast --idle-time-limit 2
# ... perform the scenes, Ctrl-D to stop ...
agg demo.cast docs/demo.gif --font-size 16   # https://github.com/asciinema/agg
```

Commit `docs/demo.gif` and embed it in the README under "Daily use":

```markdown
![Alexandria demo](docs/demo.gif)
```

(Alternative: upload the .cast to asciinema.org and embed their SVG link instead of committing a GIF -- but the GIF keeps the README self-contained and needs no external host.)

**Success condition:** README shows the recording; every step in it matches WORKFLOW.md and current skill behavior.
