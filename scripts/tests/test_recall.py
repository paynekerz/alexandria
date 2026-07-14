"""Unit tests for recall.py (ROADMAP 4.1, 4.2, 4.3).

Run from the scripts/ directory:  python -m unittest discover -s tests -v
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import recall  # noqa: E402
from recall import RecallError, concept_check, cross_project, drift, search  # noqa: E402
from vault import NoteError, Vault, save_session  # noqa: E402
from vault_lint import Linter  # noqa: E402

EXAMPLE_VAULT = Path(__file__).resolve().parent.parent.parent / "docs" / "example-vault"

# --- file-access logging (ROADMAP 4.2 DOD) -----------------------------------
# Audit hooks cannot be removed once installed, so one module-level hook
# records every file open while _RECORDING is on.
_OPENED = []
_RECORDING = False


def _audit_hook(event, args):
    if _RECORDING and event == "open" and args and isinstance(args[0], (str, bytes)):
        _OPENED.append(str(args[0]))


sys.addaudithook(_audit_hook)


def record_opens(fn):
    """Run fn, return (result, list of file paths opened while it ran)."""
    global _RECORDING
    _OPENED.clear()
    _RECORDING = True
    try:
        result = fn()
    finally:
        _RECORDING = False
    return result, list(_OPENED)


class SearchRetrieval(unittest.TestCase):
    def setUp(self):
        self.vault = Vault(EXAMPLE_VAULT)

    def test_concept_query_surfaces_prior_session(self):
        result = search(self.vault, "Atlas", "idempotency")
        notes = [s["note"] for s in result["sessions"]]
        self.assertIn("2026-06-25 retry-idempotency", notes)
        top = result["sessions"][0]
        self.assertIn("concept: Idempotency", top["matched"])
        self.assertEqual(top["commit"], "9c8d7e6")
        self.assertIn("src/jobs/retry.ts", top["files"])

    def test_glossary_heading_and_definition_match(self):
        result = search(self.vault, "Atlas", "idempotency")
        concepts = {g["concept"]: g for g in result["glossary"]}
        self.assertIn("Idempotency", concepts)
        self.assertEqual(concepts["Idempotency"]["matched"], "name")
        self.assertIn("2026-06-25 retry-idempotency", concepts["Idempotency"]["sessions"])

    def test_stem_matching_is_forgiving(self):
        # 'tokens' must reach 'Tokenization'; 'webhooks' must reach 'webhook-handling'
        result = search(self.vault, "Aurora", "tokens")
        self.assertIn("concept: Tokenization", result["sessions"][0]["matched"])
        result = search(self.vault, "Aurora", "webhooks")
        self.assertIn("2026-06-19 webhook-handling", [s["note"] for s in result["sessions"]])

    def test_taught_concepts_always_listed(self):
        result = search(self.vault, "Aurora", "zzz-no-match-zzz")
        self.assertEqual(result["sessions"], [])
        self.assertIn("Tokenization", result["taughtConcepts"])
        self.assertIn("Idempotency", result["taughtConcepts"])

    def test_more_matched_terms_ranks_first(self):
        result = search(self.vault, "Atlas", "retry backoff")
        self.assertEqual(result["sessions"][0]["note"], "2026-06-25 retry-idempotency")

    def test_unknown_project_reports_no_library(self):
        result = search(self.vault, "Nonexistent", "idempotency")
        self.assertFalse(result["projectExists"])
        self.assertEqual(result["sessions"], [])
        self.assertEqual(result["taughtConcepts"], [])

    def test_query_without_searchable_terms_refused(self):
        with self.assertRaises(RecallError):
            search(self.vault, "Atlas", "a - b")

    def test_cli_search_exits_zero(self):
        code = recall.main(["--vault", str(EXAMPLE_VAULT), "search", "Atlas", "--query", "idempotency"])
        self.assertEqual(code, 0)


class CrossProjectRestraint(unittest.TestCase):
    """ROADMAP 4.2: other projects only on explicit request or exact
    concept-index match; a default session reads no other project folder."""

    def setUp(self):
        # fresh copy under a neutral temp path so opened-file assertions can
        # match project folders precisely
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "vault"
        shutil.copytree(EXAMPLE_VAULT, self.root)
        self.vault = Vault(self.root)

    def opened_under(self, opened, *folders):
        prefixes = tuple(str((self.root / f).resolve()) for f in folders)
        return [p for p in opened if str(Path(p).resolve()).startswith(prefixes)]

    # negative case: the default retrieval pass
    def test_default_search_never_opens_other_project_folders(self):
        _, opened = record_opens(lambda: search(self.vault, "Atlas", "idempotency"))
        self.assertEqual(self.opened_under(opened, "Aurora", "Alexandria", "_Concepts"), [])
        self.assertTrue(self.opened_under(opened, "Atlas"))  # it did read its own project

    def test_concept_check_reads_only_the_concept_index(self):
        result, opened = record_opens(lambda: concept_check(self.vault, "Aurora", ["Idempotency", "Tokenization"]))
        self.assertEqual(self.opened_under(opened, "Aurora", "Atlas", "Alexandria"), [])
        self.assertEqual(result["matches"], [
            {"concept": "Idempotency", "file": "_Concepts/Idempotency.md", "otherProjects": ["Atlas"]}
        ])

    def test_concept_check_requires_exact_match(self):
        result = concept_check(self.vault, "Aurora", ["Idempotent", "idempotency"])
        self.assertEqual(result["matches"], [])

    # path (b): concept-index match -> permission -> import
    def test_cross_project_imports_the_other_projects_material(self):
        result = cross_project(self.vault, "Aurora", "Idempotency")
        self.assertEqual([m["project"] for m in result["importedFrom"]], ["Atlas"])
        atlas = result["importedFrom"][0]
        self.assertIn("2026-06-25 retry-idempotency", atlas["sessions"])
        self.assertTrue(atlas["definition"])
        self.assertTrue(any("developer.mozilla.org" in r for r in result["references"]))

    # path (a): explicit request has no index file -> honest refusal, no scan
    def test_cross_project_without_index_refuses_and_scans_nothing(self):
        def attempt():
            with self.assertRaises(RecallError):
                cross_project(self.vault, "Aurora", "Tokenization")
        _, opened = record_opens(attempt)
        self.assertEqual(self.opened_under(opened, "Atlas", "Alexandria"), [])


class DriftDetection(unittest.TestCase):
    """ROADMAP 4.3: modified covered file -> flagged; unmodified -> not
    flagged; refresh -> new note linked to its predecessor, never overwrite."""

    PROJECT = "Scriptorium"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.root = base / "vault"
        shutil.copytree(EXAMPLE_VAULT, self.root)
        self.vault = Vault(self.root)
        self.repo = base / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.py").write_text("def parse():\n    return 1\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "initial")
        self.commit = self.git("rev-parse", "--short", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=str(self.repo), check=True,
                              capture_output=True, text=True).stdout

    def payload(self, slug, commit, supersedes=None):
        lesson = f"[[{self.PROJECT}/_glossary#Parsing|Parsing]] turns raw text into structure."
        if supersedes:
            lesson += f" Refreshes [[{supersedes}]] after changes to the parser."
        p = {
            "project": self.PROJECT, "title": "How parsing works", "slug": slug,
            "date": "2026-07-13", "depth": "intro",
            "concepts": [{"name": "Parsing", "definition": "Turning raw text into structured data."}],
            "files": ["src/app.py"], "commit": commit, "sources": [], "lesson": lesson,
        }
        if supersedes:
            p["supersedes"] = supersedes
        return p

    def entry(self, report, stem):
        return next(e for e in report["sessions"] if e["note"] == stem)

    def test_full_drift_and_refresh_loop(self):
        # save a session -> unmodified repo -> not flagged
        save_session(self.vault, self.payload("how-parsing-works", self.commit))
        stem = "2026-07-13 how-parsing-works"
        report = drift(self.vault, self.PROJECT, self.repo)
        self.assertEqual(self.entry(report, stem)["status"], "fresh")
        self.assertEqual(report["stale"], [])

        # modify the covered file -> flagged, naming the file
        (self.repo / "src" / "app.py").write_text("def parse():\n    return 2\n", encoding="utf-8")
        report = drift(self.vault, self.PROJECT, self.repo)
        self.assertEqual(self.entry(report, stem)["status"], "stale")
        self.assertEqual(self.entry(report, stem)["changedFiles"], ["src/app.py"])
        self.assertEqual(report["stale"], [stem])

        # accept the refresh -> new linked note; predecessor preserved
        self.git("commit", "-qam", "change parser")
        new_commit = self.git("rev-parse", "--short", "HEAD").strip()
        save_session(self.vault, self.payload("how-parsing-works-refreshed", new_commit, supersedes=stem))
        new_stem = "2026-07-13 how-parsing-works-refreshed"
        old_note = (self.root / self.PROJECT / "Sessions" / f"{stem}.md").read_text(encoding="utf-8")
        new_note = (self.root / self.PROJECT / "Sessions" / f"{new_stem}.md").read_text(encoding="utf-8")
        self.assertIn(f"supersedes: {stem}", new_note)
        self.assertIn(f"[[{stem}]]", new_note)
        self.assertIn("## Lesson", old_note)  # predecessor still intact, not overwritten

        # predecessor now reports superseded, successor fresh; vault lints clean
        report = drift(self.vault, self.PROJECT, self.repo)
        self.assertEqual(self.entry(report, stem)["status"], "superseded")
        self.assertEqual(self.entry(report, stem)["supersededBy"], new_stem)
        self.assertEqual(self.entry(report, new_stem)["status"], "fresh")
        self.assertEqual(report["stale"], [])
        self.assertEqual(Linter(self.vault).run(), [])

    def test_unversioned_session_is_unverifiable_not_guessed(self):
        save_session(self.vault, self.payload("how-parsing-works", "unversioned"))
        report = drift(self.vault, self.PROJECT, self.repo)
        entry = self.entry(report, "2026-07-13 how-parsing-works")
        self.assertEqual(entry["status"], "unverifiable")
        self.assertNotIn("2026-07-13 how-parsing-works", report["stale"])

    def test_unknown_commit_is_unverifiable(self):
        save_session(self.vault, self.payload("how-parsing-works", "deadbee"))
        report = drift(self.vault, self.PROJECT, self.repo)
        self.assertEqual(self.entry(report, "2026-07-13 how-parsing-works")["status"], "unverifiable")

    def test_non_repo_refused(self):
        with self.assertRaises(RecallError):
            drift(self.vault, "Atlas", Path(self._tmp.name) / "nowhere")

    def test_refresh_must_name_existing_predecessor(self):
        with self.assertRaises(NoteError):
            save_session(self.vault, self.payload("refresh", self.commit, supersedes="2026-01-01 ghost"))

    def test_refresh_lesson_must_link_predecessor(self):
        save_session(self.vault, self.payload("how-parsing-works", self.commit))
        bad = self.payload("refresh", self.commit, supersedes="2026-07-13 how-parsing-works")
        bad["lesson"] = f"[[{self.PROJECT}/_glossary#Parsing|Parsing]] without the predecessor link."
        with self.assertRaises(NoteError):
            save_session(self.vault, bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
