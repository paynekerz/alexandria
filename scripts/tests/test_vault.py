"""Unit tests for vault.py (ROADMAP 1.2 DOD).

Run from the scripts/ directory:  python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from vault import Vault, VaultError, VaultPathError  # noqa: E402


class VaultTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def make_config(self, vault_path):
        cfg_dir = self.base / ".alexandria"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = dict(config.DEFAULTS)
        cfg["vaultPath"] = str(vault_path)
        (cfg_dir / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        os.environ["ALEXANDRIA_CONFIG_DIR"] = str(cfg_dir)
        self.addCleanup(os.environ.pop, "ALEXANDRIA_CONFIG_DIR", None)


class TestPathResolution(VaultTestCase):
    def test_default_path_expands_under_home(self):
        # the shipped default must expand to an absolute path inside the user's home
        expanded = config.expand_path(config.DEFAULTS["vaultPath"])
        self.assertTrue(expanded.is_absolute())
        self.assertEqual(expanded, Path.home().resolve() / "Desktop" / "Alexandria")

    def test_custom_path_from_config(self):
        custom = self.base / "MyVault"
        self.make_config(custom)
        vault = Vault.from_config()
        self.assertEqual(vault.root, custom.resolve())

    def test_resolve_inside_root(self):
        vault = Vault(self.base / "V")
        target = vault.resolve("Aurora/Sessions/note.md")
        self.assertEqual(target, (self.base / "V" / "Aurora" / "Sessions" / "note.md").resolve())

    def test_internal_dotdot_that_stays_inside_is_allowed(self):
        vault = Vault(self.base / "V")
        self.assertEqual(vault.resolve("A/../B/note.md"), vault.resolve("B/note.md"))

    def test_root_inside_git_dir_refused(self):
        with self.assertRaises(VaultError):
            Vault(self.base / ".git" / "vault")

    def test_root_that_is_a_file_refused(self):
        f = self.base / "afile"
        f.write_text("x", encoding="utf-8")
        with self.assertRaises(VaultError):
            Vault(f)


class TestTraversalRefused(VaultTestCase):
    def setUp(self):
        super().setUp()
        self.vault = Vault(self.base / "V")
        self.vault.ensure_root()

    def assert_refused(self, relative):
        with self.assertRaises(VaultPathError, msg=relative):
            self.vault.resolve(relative)
        # and nothing may have been created outside the root
        self.assertEqual(
            [p.name for p in self.base.iterdir()], ["V"], f"{relative} created something outside the vault"
        )

    def test_parent_traversal(self):
        self.assert_refused("../evil.md")

    def test_backslash_parent_traversal(self):
        self.assert_refused("..\\evil.md")

    def test_nested_traversal_escaping(self):
        self.assert_refused("Aurora/../../evil.md")

    def test_deep_traversal(self):
        self.assert_refused("../../../../../../tmp/evil.md")

    def test_absolute_path_posix(self):
        self.assert_refused(str(self.base / "evil.md"))

    def test_absolute_path_drive(self):
        self.assert_refused("C:\\Windows\\evil.md")

    def test_write_note_traversal_refused(self):
        with self.assertRaises(VaultPathError):
            self.vault.write_note("../evil.md", "content")
        self.assertFalse((self.base / "evil.md").exists())


class TestWrites(VaultTestCase):
    def setUp(self):
        super().setUp()
        self.vault = Vault(self.base / "V")
        self.vault.ensure_root()

    def test_ensure_project_creates_sessions_dir(self):
        path = self.vault.ensure_project("Aurora")
        self.assertTrue(path.is_dir())
        self.assertEqual(path, (self.base / "V" / "Aurora" / "Sessions").resolve())

    def test_ensure_project_refuses_reserved_names(self):
        for bad in ("_Concepts", ".alexandria", "_anything"):
            with self.assertRaises(VaultError, msg=bad):
                self.vault.ensure_project(bad)

    def test_write_note_atomic_roundtrip(self):
        target = self.vault.write_note("Aurora/Sessions/2026-07-09 test.md", "---\nbody\n")
        self.assertEqual(target.read_text(encoding="utf-8"), "---\nbody\n")
        leftovers = list(target.parent.glob("*.tmp"))
        self.assertEqual(leftovers, [], "temp file leaked")

    def test_write_note_overwrites_atomically(self):
        rel = "Aurora/Sessions/2026-07-09 test.md"
        self.vault.write_note(rel, "old")
        self.vault.write_note(rel, "new")
        self.assertEqual(self.vault.read_note(rel), "new")

    def test_unwritable_location(self):
        # a path whose parent is a FILE is reliably unwritable on every platform
        (self.base / "V" / "blocker").write_text("x", encoding="utf-8")
        with self.assertRaises(VaultError):
            self.vault.write_note("blocker/nested/note.md", "content")

    def test_unwritable_vault_root(self):
        blocker = self.base / "rootfile"
        blocker.write_text("x", encoding="utf-8")
        with self.assertRaises(VaultError):
            Vault(blocker / "vault").ensure_root()


if __name__ == "__main__":
    unittest.main(verbosity=2)
