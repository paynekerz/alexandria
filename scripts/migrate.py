"""Alexandria vault schema migration scaffold (ROADMAP 3.6).

The librarian refuses all writes when a vault's `.alexandria/meta.json`
`schemaVersion` differs from the version this code writes
(`vault.VAULT_SCHEMA_VERSION`), and points here. This script walks the vault
forward one registered migration at a time until it reaches the current
version, updating `meta.json` after each successful step.

How future migrations register
------------------------------
Add one entry to MIGRATIONS mapping the SOURCE version to a
(TARGET_version, migration_function) pair, e.g. when schema v2 lands:

    def migrate_v1_to_v2(vault):
        '''Rewrite every note from v1 to v2. Must leave the vault fully
        valid at v2 (vault_lint.py clean) and return a list of change
        descriptions. All writes through the Vault instance.'''
        ...

    MIGRATIONS[1] = (2, migrate_v1_to_v2)

Rules a migration function must obey:
  1. Idempotent per step is not required — meta.json is bumped only after the
     function returns, so a crash mid-step leaves the vault marked at the
     source version and the step re-runs.
  2. Never write outside the vault (use the passed Vault; it enforces this).
  3. Lossless: content survives; only shape changes.
  4. The chain must strictly increase the version (enforced below).

Today there is exactly one (no-op) migration shape on file: v1 is the first
schema, so `_migrate_v1_to_v1` exists purely as the worked example of the
registration contract and is never executed — a vault already at the current
version exits before the chain is consulted.

CLI:
    python migrate.py [--vault PATH]      (default: vaultPath from config)

Exit codes: 0 already current / migrated, 1 vault not migratable (no
registered path, or not an Alexandria vault), 2 config problem.
"""
import argparse
import json
import sys

from config import ConfigError
from vault import VAULT_SCHEMA_VERSION, Vault, VaultError


def _migrate_v1_to_v1(vault):
    """Worked example of the migration contract — a lossless no-op."""
    return []


MIGRATIONS = {
    1: (1, _migrate_v1_to_v1),
}


def read_version(vault):
    meta_file = vault.resolve(".alexandria/meta.json")
    if not meta_file.is_file():
        raise VaultError(f"{vault.root} is not an Alexandria vault (no .alexandria/meta.json)")
    try:
        return json.loads(meta_file.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as e:
        raise VaultError(f".alexandria/meta.json is not valid JSON ({e})")


def write_version(vault, meta, version):
    meta = dict(meta)
    meta["schemaVersion"] = version
    vault.write_note(".alexandria/meta.json", json.dumps(meta, indent=2) + "\n")


def migrate(vault):
    """Returns (final_version, [messages]). Raises VaultError when stuck."""
    meta, _ = read_version(vault)
    version = meta.get("schemaVersion")
    messages = []
    if version == VAULT_SCHEMA_VERSION:
        return version, [f"already at current schemaVersion {version} — nothing to do"]
    while version != VAULT_SCHEMA_VERSION:
        if version not in MIGRATIONS:
            raise VaultError(
                f"no migration registered from schemaVersion {version!r}. "
                f"This vault predates schema v1 or its meta.json was edited by hand; "
                f"restore .alexandria/meta.json from backup or open an issue."
            )
        target, step = MIGRATIONS[version]
        if not isinstance(target, int) or target <= (version if isinstance(version, int) else 0):
            raise VaultError(
                f"invalid registration: migration from {version} targets {target}; the chain must strictly increase"
            )
        messages.extend(step(vault) or [])
        meta, _ = read_version(vault)
        write_version(vault, meta, target)
        messages.append(f"migrated {version} -> {target}")
        version = target
    messages.append("done — run 'python vault_lint.py' to verify the vault")
    return version, messages


def main(argv=None):
    parser = argparse.ArgumentParser(description="Migrate an Alexandria vault to the current schema version.")
    parser.add_argument("--vault", help="vault root (default: vaultPath from ~/.alexandria/config.json)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(errors="replace")
    try:
        vault = Vault(args.vault) if args.vault else Vault.from_config()
        final, messages = migrate(vault)
    except FileNotFoundError:
        print("No Alexandria config — pass --vault or run scripts/setup.py.", file=sys.stderr)
        return 2
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        return 2
    except VaultError as e:
        print(str(e), file=sys.stderr)
        return 1
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
