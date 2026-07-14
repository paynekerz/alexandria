"""Unit tests for recall.py (ROADMAP 4.1).

Run from the scripts/ directory:  python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import recall  # noqa: E402
from recall import RecallError, search  # noqa: E402
from vault import Vault  # noqa: E402

EXAMPLE_VAULT = Path(__file__).resolve().parent.parent.parent / "docs" / "example-vault"


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
