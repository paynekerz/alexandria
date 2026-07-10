"""Unit tests for migrate.py (ROADMAP 3.6).

Run from the scripts/ directory:  python -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import migrate  # noqa: E402
from vault import Vault, VaultError  # noqa: E402


class MigrateTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "vault"
        (self.root / ".alexandria").mkdir(parents=True)
        self.vault = Vault(self.root)

    def set_version(self, version):
        (self.root / ".alexandria" / "meta.json").write_text(
            json.dumps({"schemaVersion": version, "generator": "alexandria"}), encoding="utf-8"
        )

    def get_version(self):
        return json.loads((self.root / ".alexandria" / "meta.json").read_text(encoding="utf-8"))["schemaVersion"]

    def test_current_vault_is_noop(self):
        self.set_version(1)
        final, messages = migrate.migrate(self.vault)
        self.assertEqual(final, 1)
        self.assertIn("nothing to do", messages[0])
        self.assertEqual(self.get_version(), 1)

    def test_unknown_version_refused(self):
        self.set_version(0)
        with self.assertRaises(VaultError):
            migrate.migrate(self.vault)
        self.assertEqual(self.get_version(), 0, "meta.json must be untouched on refusal")

    def test_registered_chain_runs_and_bumps_meta(self):
        self.set_version(0)
        calls = []
        original = dict(migrate.MIGRATIONS)
        migrate.MIGRATIONS[0] = (1, lambda vault: calls.append("ran") or ["rewrote 0 notes"])
        self.addCleanup(lambda: (migrate.MIGRATIONS.clear(), migrate.MIGRATIONS.update(original)))
        final, messages = migrate.migrate(self.vault)
        self.assertEqual(final, 1)
        self.assertEqual(calls, ["ran"])
        self.assertEqual(self.get_version(), 1)
        self.assertIn("migrated 0 -> 1", messages)

    def test_non_increasing_registration_refused(self):
        self.set_version(0)
        original = dict(migrate.MIGRATIONS)
        migrate.MIGRATIONS[0] = (0, lambda vault: [])
        self.addCleanup(lambda: (migrate.MIGRATIONS.clear(), migrate.MIGRATIONS.update(original)))
        with self.assertRaises(VaultError):
            migrate.migrate(self.vault)

    def test_not_a_vault_refused(self):
        (self.root / ".alexandria" / "meta.json").unlink(missing_ok=True)
        with self.assertRaises(VaultError):
            migrate.migrate(self.vault)


if __name__ == "__main__":
    unittest.main(verbosity=2)
