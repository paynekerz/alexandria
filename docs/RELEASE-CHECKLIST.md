# Release Checklist

Every item must pass before a release is tagged.

## 1. Test and lint gates

- [ ] **Unit tests green.** From the repo root: `python -m pytest scripts/tests/ -q` (or `python -m unittest discover scripts/tests`). All 71 tests pass.
- [ ] **Markdown lint green.** The `markdown-lint` CI workflow passes on the release commit.
- [ ] **No untracked local-only files in the tag.** `git ls-files | grep -E "STYLE|PROMPTS|ROADMAP|CLAUDE"` returns nothing; `git log --all -- STYLE.md` is empty.
- [ ] **Trigger-eval extrapolation still valid.** Every SKILL.md frontmatter `description` is byte-identical to the `original_description` in that skill's newest `evals/results/5.1-trigger/<skill>/*/results.json`, and the eval sets and invocation-visible names are unchanged (Decision 16). If anything differs, the 7.2 extrapolation (`evals/results/7.2-description/SUMMARY.md`) no longer holds -- re-run the description optimization loop (or at minimum the section 4 baseline eval) before tagging.

## 2. Token budget gate

- [ ] **No session type regresses more than 20% over its token baseline.**

  Run from the repo root:

  ```bash
  python evals/benchmark/run_token_benchmark.py --check
  ```

  This re-measures all three representative session types (3 live headless runs each) and compares each type's mean total tokens against the recorded baselines in `evals/benchmark/baseline.json`. Exit code `0` means every type is within budget; exit code `1` means at least one type exceeded its baseline mean by more than 20% -- **the release is blocked** until the regression is fixed or, if the growth is a deliberate documented trade-off, the baseline is re-recorded in the same commit as the change that justifies it (update `docs/BENCHMARKS.md` too, and say why in the commit message).

  **Status note (2026-07-18):** `evals/benchmark/baseline.json` and `docs/BENCHMARKS.md` have not been recorded yet -- measurement runs exist in `evals/results/5.3-benchmark/` but the baseline was never frozen. `--check` cannot run until that lands. Either finish recording the baseline or explicitly waive this gate for v1.0.0 in the release commit message.

## 3. Package the artifacts

- [ ] Build per-skill zips and the full-suite zip into `dist/`:

  ```bash
  export PYTHONIOENCODING=utf-8   # Windows: package_skill.py prints emoji
  python <skill-creator>/scripts/package_skill.py skills/alexandria-teach dist
  python <skill-creator>/scripts/package_skill.py skills/alexandria-librarian dist
  python <skill-creator>/scripts/package_skill.py skills/alexandria-recall dist
  ```

  plus `alexandria-v<version>-full.zip` containing `skills/`, `scripts/`, `agents/`, `templates/`, `docs/`, README, LICENSE, CHANGELOG. Each per-skill zip must pass `quick_validate` (package_skill runs it automatically).

## 4. Clean-machine verification (from the release artifacts, not the repo)

Do this on a machine (or fresh user account / container) that has never had Alexandria installed. Only the release artifacts and the README are allowed -- if you need anything else, the README failed its DOD.

- [ ] Download `alexandria-v<version>-full.zip` from the draft release; unpack.
- [ ] Follow the README's Install section only: skill folders into `~/.claude/skills/`, `scripts/`, `agents/`, `templates/` into `~/.claude/`.
- [ ] README Success condition holds: three `alexandria-*` folders under `~/.claude/skills/`, `~/.claude/scripts/config.py` exists.
- [ ] `python ~/.claude/scripts/config.py` exits `1` with the "run the first-run setup" message (no config yet -- expected).
- [ ] In a real project, invoke `alexandria-teach`; the first-run interview runs once, `~/.alexandria/config.json` is written, the vault is scaffolded, the teacher agent lands in `~/.claude/agents/alexandria-teacher.md` with the chosen model, and the originally requested lesson happens in the same turn.
- [ ] Complete one full loop per the README: teach -> save -> recall surfaces the saved lesson -> `python ~/.claude/scripts/vault_lint.py` reports `clean: 0 findings`.
- [ ] Second invocation of any skill skips the interview.

- [ ] **Phase 5 trigger evals pass against the release artifacts.** Point the eval sets at the *installed* skills (the unpacked artifact copies, not the repo checkout). Requires Python 3.10+ for the tooling (3.14 used for the 5.1 results) and a `claude` CLI login. From `evals/tooling/`:

  ```bash
  py -3.14 -m scripts.run_loop --eval-set ../trigger/alexandria-teach.trigger.json \
      --skill-path ~/.claude/skills/alexandria-teach --max-iterations 1 --model <model>
  py -3.14 -m scripts.run_loop --eval-set ../trigger/alexandria-librarian.trigger.json \
      --skill-path ~/.claude/skills/alexandria-librarian --max-iterations 1 --model <model>
  py -3.14 -m scripts.run_loop --eval-set ../trigger/alexandria-recall.trigger.json \
      --skill-path ~/.claude/skills/alexandria-recall --max-iterations 1 --model <model>
  ```

  Pass condition per skill (same as 5.1's DOD): positive trigger rate >= 90%, false-trigger rate <= 5%, session-limit errors excluded from rates.

## 5. Publish

- [ ] CHANGELOG has a dated entry for the version; known issues listed honestly.
- [ ] Tag `v<version>` on the release commit; push the tag.
- [ ] GitHub release created with the release notes and all four zips attached.
- [ ] README install instructions point at the release URL and work as written (spot-check the clone/download path in the notes).
