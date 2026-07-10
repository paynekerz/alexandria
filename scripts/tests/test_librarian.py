"""Unit tests for the save pipeline in vault.py (ROADMAP 3.1-3.4).

The strongest assertions here compare regenerated output byte-for-byte against
the hand-built example vault from Phase 0.3 — the frozen schema reference.

Run from the scripts/ directory:  python -m unittest discover -s tests -v
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vault as v  # noqa: E402
from vault import (  # noqa: E402
    NoteError,
    Vault,
    VaultError,
    VaultSchemaError,
    parse_frontmatter,
    parse_glossary,
    render_concept_file,
    render_glossary,
    render_index,
    save_session,
    serialize_frontmatter,
)

EXAMPLE_VAULT = Path(__file__).resolve().parent.parent.parent / "docs" / "example-vault"


def read(path):
    return path.read_text(encoding="utf-8")


def make_payload(**overrides):
    payload = {
        "project": "Aurora",
        "title": "How refunds flow back",
        "slug": "refund-flow",
        "date": "2026-07-09",
        "depth": "intro",
        "concepts": [
            {"name": "Refund Flow", "definition": "How money travels back to the shopper after a refund."},
        ],
        "files": ["src/Refund/Handler.php"],
        "commit": "abc1234",
        "sources": [],
        "lesson": "A refund starts here: [[Aurora/_glossary#Refund Flow|refund flow]].",
    }
    payload.update(overrides)
    return payload


class ExampleVaultRegen(unittest.TestCase):
    """Derived files must regenerate byte-identically from frontmatter alone."""

    @classmethod
    def setUpClass(cls):
        cls.vault = Vault(EXAMPLE_VAULT)

    def test_frontmatter_roundtrip_every_session(self):
        for project in ("Aurora", "Atlas"):
            for path in sorted((EXAMPLE_VAULT / project / "Sessions").glob("*.md")):
                original = read(path)
                meta, body = parse_frontmatter(original)
                rebuilt = serialize_frontmatter(meta, v.SESSION_FIELD_ORDER) + body
                self.assertEqual(rebuilt, original, path.name)

    def test_index_regen_byte_identical(self):
        for project in ("Aurora", "Atlas"):
            sessions = v.load_sessions(self.vault, project)
            rendered = render_index(project, sessions)
            self.assertEqual(rendered, read(EXAMPLE_VAULT / project / "_index.md"), project)

    def test_glossary_roundtrip_byte_identical(self):
        for project in ("Aurora", "Atlas"):
            original = read(EXAMPLE_VAULT / project / "_glossary.md")
            _, entries = parse_glossary(original)
            self.assertEqual(render_glossary(project, entries), original, project)

    def test_concept_file_regen_byte_identical(self):
        per_project = v.concept_map(self.vault)["Idempotency"]
        rendered = render_concept_file("Idempotency", per_project)
        self.assertEqual(rendered, read(EXAMPLE_VAULT / "_Concepts" / "Idempotency.md"))

    def test_single_project_concepts_get_no_file(self):
        concept_files = {p.stem for p in (EXAMPLE_VAULT / "_Concepts").glob("*.md")}
        multi = {c for c, per in v.concept_map(self.vault).items() if len(per) >= 2}
        self.assertEqual(concept_files, multi)


class SavePipeline(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "V"
        self.vault = Vault(self.root)
        self.vault.ensure_root()
        meta_dir = self.root / ".alexandria"
        meta_dir.mkdir()
        (meta_dir / "meta.json").write_text(json.dumps({"schemaVersion": 1}), encoding="utf-8")

    def test_save_creates_note_glossary_index(self):
        result = save_session(self.vault, make_payload())
        note = read(self.root / "Aurora" / "Sessions" / "2026-07-09 refund-flow.md")
        self.assertTrue(note.startswith("---\nproject: Aurora\ntitle: How refunds flow back\n"))
        self.assertIn("## Lesson", note)
        self.assertIn("- `src/Refund/Handler.php` @ `abc1234`", note)
        self.assertNotIn("## Sources", note)  # sources empty -> section omitted
        meta, _ = parse_frontmatter(note)
        self.assertEqual(meta["schemaVersion"], 1)
        glossary = read(self.root / "Aurora" / "_glossary.md")
        self.assertIn("## Refund Flow", glossary)
        self.assertIn("Sessions: [[2026-07-09 refund-flow]]", glossary)
        index = read(self.root / "Aurora" / "_index.md")
        self.assertIn("| 2026-07-09 | [[2026-07-09 refund-flow]] | intro | Refund Flow | src/Refund/Handler.php | abc1234 |", index)
        self.assertEqual(result["glossaryAdded"], ["Refund Flow"])
        self.assertEqual(result["conceptFiles"], [])

    def test_second_session_appends_glossary_link_not_definition(self):
        save_session(self.vault, make_payload())
        save_session(self.vault, make_payload(
            title="Refunds under retries", slug="refund-retries", date="2026-07-10",
            concepts=[{"name": "Refund Flow", "definition": "IGNORED — must not replace the original."}],
            lesson="Retries meet [[Aurora/_glossary#Refund Flow|refund flow]] again.",
        ))
        glossary = read(self.root / "Aurora" / "_glossary.md")
        self.assertEqual(glossary.count("## Refund Flow"), 1)
        self.assertIn("Sessions: [[2026-07-09 refund-flow]], [[2026-07-10 refund-retries]]", glossary)
        self.assertIn("How money travels back", glossary)
        self.assertNotIn("IGNORED", glossary)

    def test_concept_file_appears_only_at_second_project(self):
        save_session(self.vault, make_payload())
        concept_file = self.root / "_Concepts" / "Refund Flow.md"
        self.assertFalse(concept_file.exists())
        save_session(self.vault, make_payload(
            project="Borealis", slug="refund-flow-b", date="2026-07-11",
            lesson="Borealis refunds: [[Borealis/_glossary#Refund Flow|refund flow]].",
        ))
        self.assertTrue(concept_file.exists())
        content = read(concept_file)
        self.assertIn("Taught in 2 projects.", content)
        self.assertIn("Glossary: [[Aurora/_glossary#Refund Flow|Refund Flow in Aurora]]", content)
        self.assertIn("Glossary: [[Borealis/_glossary#Refund Flow|Refund Flow in Borealis]]", content)

    def test_quiz_lands_in_frontmatter_and_body(self):
        save_session(self.vault, make_payload(quiz={
            "score": "1/2",
            "rows": [
                {"question": "Where does a refund start?", "result": "Correct"},
                {"question": "Who issues the credit?", "result": "Incorrect"},
            ],
        }))
        note = read(self.root / "Aurora" / "Sessions" / "2026-07-09 refund-flow.md")
        self.assertIn('quizScore: "1/2"', note)
        self.assertIn("## Comprehension", note)
        self.assertIn("| 2 | Who issues the credit? | Incorrect |", note)
        self.assertIn("Score: 1/2", note)

    def test_duplicate_session_refused(self):
        save_session(self.vault, make_payload())
        with self.assertRaises(VaultError):
            save_session(self.vault, make_payload())

    def test_schema_mismatch_refuses_before_any_write(self):
        (self.root / ".alexandria" / "meta.json").write_text(json.dumps({"schemaVersion": 0}), encoding="utf-8")
        with self.assertRaises(VaultSchemaError):
            save_session(self.vault, make_payload())
        self.assertFalse((self.root / "Aurora").exists(), "refusal must not leave partial writes")

    def test_missing_meta_json_refused(self):
        shutil.rmtree(self.root / ".alexandria")
        with self.assertRaises(VaultError):
            save_session(self.vault, make_payload())


class PayloadValidation(unittest.TestCase):
    def problems(self, **overrides):
        return v.payload_problems(make_payload(**overrides))

    def test_valid_payload_has_no_problems(self):
        self.assertEqual(self.problems(), [])

    def test_lesson_must_wikilink_every_concept(self):
        problems = self.problems(lesson="No links here at all.")
        self.assertTrue(any("must wiki-link" in p for p in problems))

    def test_lesson_may_not_contain_urls(self):
        problems = self.problems(
            lesson="See https://example.com and [[Aurora/_glossary#Refund Flow|refund flow]].")
        self.assertTrue(any("invariant 7" in p for p in problems))

    def test_bad_depth_date_and_forbidden_concept_name(self):
        problems = v.payload_problems(make_payload(
            depth="expert", date="July 9",
            concepts=[{"name": "A/B Testing", "definition": "x"}],
        ))
        joined = "\n".join(problems)
        self.assertIn("depth:", joined)
        self.assertIn("date:", joined)
        self.assertIn("forbidden filename character", joined)

    def test_new_concept_without_definition_rejected_at_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "V"
            vault = Vault(root)
            vault.ensure_root()
            (root / ".alexandria").mkdir()
            (root / ".alexandria" / "meta.json").write_text(json.dumps({"schemaVersion": 1}), encoding="utf-8")
            with self.assertRaises(NoteError):
                save_session(vault, make_payload(concepts=[{"name": "Refund Flow"}]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
