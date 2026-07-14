"""Unit tests for vault_lint.py (ROADMAP 3.5).

Run from the scripts/ directory:  python -m unittest discover -s tests -v
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vault_lint  # noqa: E402
from vault import Vault, VaultError  # noqa: E402
from vault_lint import Linter, repair  # noqa: E402

EXAMPLE_VAULT = Path(__file__).resolve().parent.parent.parent / "docs" / "example-vault"


def kinds(findings):
    return {f["kind"] for f in findings}


class LintCleanBaseline(unittest.TestCase):
    def test_example_vault_is_clean(self):
        self.assertEqual(Linter(Vault(EXAMPLE_VAULT)).run(), [])


class LintDefectClasses(unittest.TestCase):
    """One injected defect per class; lint must catch each; repair must
    restore derived files. Each test gets its own scratch copy."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "vault"
        shutil.copytree(EXAMPLE_VAULT, self.root)
        self.vault = Vault(self.root)

    def lint(self):
        linter = Linter(self.vault)
        return linter, linter.run()

    def test_frontmatter_defect(self):
        note = self.root / "Atlas" / "Sessions" / "2026-07-01 request-pipeline.md"
        note.write_text(note.read_text(encoding="utf-8").replace("depth: intro", "depth: expert"), encoding="utf-8")
        _, findings = self.lint()
        self.assertIn("frontmatter", kinds(findings))

    def test_dead_wikilink(self):
        note = self.root / "Aurora" / "Sessions" / "2026-06-19 webhook-handling.md"
        note.write_text(note.read_text(encoding="utf-8") + "\nSee [[2026-01-01 ghost-session]].\n", encoding="utf-8")
        _, findings = self.lint()
        self.assertIn("dead-link", kinds(findings))

    def test_dead_heading_link(self):
        note = self.root / "Aurora" / "Sessions" / "2026-06-19 webhook-handling.md"
        note.write_text(note.read_text(encoding="utf-8") + "\n[[Aurora/_glossary#No Such Concept|x]]\n", encoding="utf-8")
        _, findings = self.lint()
        self.assertIn("dead-link", kinds(findings))

    def test_orphaned_glossary_entry(self):
        glossary = self.root / "Aurora" / "_glossary.md"
        glossary.write_text(
            glossary.read_text(encoding="utf-8") + "\n## Quantum Tunneling\n\nNobody teaches this.\n\nSessions: [[2026-06-12 checkout-tokenization-flow]]\n",
            encoding="utf-8",
        )
        _, findings = self.lint()
        self.assertIn("glossary", kinds(findings))

    def test_index_drift_caught_and_repaired(self):
        index = self.root / "Aurora" / "_index.md"
        pristine = index.read_text(encoding="utf-8")
        index.write_text(pristine.replace("a1b2c3d", "EDITED0"), encoding="utf-8")
        linter, findings = self.lint()
        self.assertIn("drift", kinds(findings))
        repair(self.vault, linter)
        self.assertEqual(index.read_text(encoding="utf-8"), pristine)
        self.assertEqual(Linter(self.vault).run(), [])

    def test_stale_concept_file_caught_and_removed(self):
        bogus = self.root / "_Concepts" / "Middleware.md"
        bogus.write_text("---\nconcept: Middleware\nprojects:\n  - Atlas\nschemaVersion: 1\n---\n\n# Middleware\n", encoding="utf-8")
        linter, findings = self.lint()
        self.assertIn("drift", kinds(findings))
        repair(self.vault, linter)
        self.assertFalse(bogus.exists())
        self.assertEqual(Linter(self.vault).run(), [])

    def test_source_url_outside_sources_section(self):
        note = self.root / "Atlas" / "Sessions" / "2026-06-25 retry-idempotency.md"
        note.write_text(note.read_text(encoding="utf-8").replace(
            "Atlas talks to services", "See https://example.com — Atlas talks to services"), encoding="utf-8")
        _, findings = self.lint()
        self.assertIn("sources", kinds(findings))

    def test_dead_supersedes_predecessor(self):
        note = self.root / "Atlas" / "Sessions" / "2026-07-01 request-pipeline.md"
        note.write_text(note.read_text(encoding="utf-8").replace(
            "commit: 3f2e1d0", "commit: 3f2e1d0\nsupersedes: 2026-01-01 ghost-session"), encoding="utf-8")
        _, findings = self.lint()
        self.assertIn("dead-link", kinds(findings))

    def test_bad_meta_json(self):
        meta = self.root / ".alexandria" / "meta.json"
        meta.write_text('{"schemaVersion": 0}', encoding="utf-8")
        _, findings = self.lint()
        self.assertIn("meta", kinds(findings))

    def test_repair_refuses_while_frontmatter_broken(self):
        note = self.root / "Atlas" / "Sessions" / "2026-07-01 request-pipeline.md"
        note.write_text(note.read_text(encoding="utf-8").replace("depth: intro", "depth: expert"), encoding="utf-8")
        linter, _ = self.lint()
        with self.assertRaises(VaultError):
            repair(self.vault, linter)


if __name__ == "__main__":
    unittest.main(verbosity=2)
