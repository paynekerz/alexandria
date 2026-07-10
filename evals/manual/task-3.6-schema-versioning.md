# Manual test — Task 3.6 (schema versioning & migration scaffold)

Two halves: the librarian's write refusal on version mismatch (`check_vault_schema` in `scripts/vault.py`, called by `save_session` before any write), and the migration scaffold `scripts/migrate.py` (v1→v1 no-op with the registration contract documented in its module docstring).

## Demo — vault doctored to `schemaVersion: 0`

Scratch copy of the example vault, `.alexandria/meta.json` edited to `"schemaVersion": 0`.

**1. Librarian save → refused, exit 3, no writes:**

```text
$ python vault.py save-session < payload.json
refused: vault schemaVersion is 0 but this Alexandria writes version 1.
No writes performed. Run 'python scripts/migrate.py' to bring the vault up to date.
exit: 3
```

Verified afterward: the payload's project folder was never created — the check runs before the first write. The librarian SKILL.md branches on exit 3 and relays this message verbatim, never retrying or touching `meta.json`.

**2. `migrate.py` on the v0 vault → honest no-path message, exit 1:**

```text
no migration registered from schemaVersion 0. This vault predates schema v1 or
its meta.json was edited by hand; restore .alexandria/meta.json from backup or
open an issue.
exit: 1
```

There is genuinely no v0; inventing a v0→v1 rewrite would be a guess (Axiom 3), so the scaffold says so instead.

**3. `migrate.py` on a current v1 vault → scaffold runs, no-op, exit 0:**

```text
already at current schemaVersion 1 — nothing to do
exit: 0
```

## Registration contract (for future migrations)

Documented in the `migrate.py` docstring with `_migrate_v1_to_v1` as the worked example: add `MIGRATIONS[1] = (2, migrate_v1_to_v2)`; the function gets a `Vault` (root-guarded writes only), must be lossless and leave the vault `vault_lint.py`-clean; `meta.json` is bumped only after the step returns, so a crash re-runs the step; the chain must strictly increase (enforced — a non-increasing registration raises instead of looping).

## Regression tests

`scripts/tests/test_migrate.py`: no-op on current vault, refusal on unknown version (meta untouched), a temporarily-registered 0→1 chain runs and bumps `meta.json`, non-increasing registration refused, non-vault refused. Plus `test_librarian.py::test_schema_mismatch_refuses_before_any_write`. Full suite 51/51 green.
