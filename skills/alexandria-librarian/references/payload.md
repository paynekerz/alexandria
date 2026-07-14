# save-session payload reference

`python scripts/vault.py save-session` reads one JSON object from stdin and performs the whole save pipeline (note → glossary → index → cross-project concepts). Exit codes: `0` saved, `2` payload/path refused (stderr lists every problem), `3` vault schemaVersion mismatch (run `scripts/migrate.py`).

## Fields

| Field | Type | Required | Rules |
|---|---|---|---|
| `project` | string | yes | Vault folder name. No leading `.`/`_`, no `\ / : * ? " < > \| # ^ [ ]`. |
| `title` | string | yes | Human-readable lesson title. |
| `slug` | string | no | Kebab-case filename slug. Default: kebab-cased title. Note becomes `<project>/Sessions/<date> <slug>.md`; saving refuses if that file exists. |
| `date` | string | yes | `YYYY-MM-DD`. |
| `depth` | string | yes | `intro` \| `practitioner` \| `deep-dive`. |
| `concepts` | array | yes, ≥ 1 | Objects `{"name", "definition"}`. `name` is the canonical Title Case concept. `definition` is a one-paragraph intro-level definition — used only when the concept is new to this project's glossary (existing definitions are never overwritten), but required then, so always provide it. |
| `files` | string[] | yes | Repo-relative paths the lesson explained. May be `[]`. |
| `commit` | string | yes | Short or full git hash at teach time, or `unversioned`. |
| `sources` | array | yes | Objects `{"title", "url"}`, verified-alive links only. May be `[]`. |
| `lesson` | string | yes | Markdown prose of the `## Lesson` section. Must wiki-link each concept's glossary entry (`[[<project>/_glossary#<name>\|display]]`) at first mention. Must contain no raw URLs — external links belong in `sources`. |
| `quiz` | object | no | `{"score": "<correct>/<asked>", "rows": [{"question", "result"}, ...]}`. Only when a comprehension check actually ran. |
| `supersedes` | string | no | Only on a drift refresh (recall names the stale note): the predecessor session's filename stem, e.g. `"2026-06-25 retry-idempotency"`. Must name an existing note in this project's `Sessions/`, and `lesson` must link it (`[[<stem>]]`) — the script refuses otherwise. The predecessor is never modified. |

The script composes everything else itself: frontmatter (fixed field order, `schemaVersion: 1`), `## Files` (from `files` + `commit`), `## Sources` (from `sources`), `## Comprehension` (from `quiz`).

## Worked example

```json
{
  "project": "Aurora",
  "title": "How checkout tokenization works",
  "slug": "checkout-tokenization-flow",
  "date": "2026-06-12",
  "depth": "intro",
  "concepts": [
    {
      "name": "Tokenization",
      "definition": "Swapping a sensitive value (like a card number) for a meaningless stand-in token issued by the party that holds the real value."
    }
  ],
  "files": ["src/Checkout/TokenizeHandler.php"],
  "commit": "a1b2c3d",
  "sources": [
    {
      "title": "Idempotent — MDN Glossary",
      "url": "https://developer.mozilla.org/en-US/docs/Glossary/Idempotent"
    }
  ],
  "lesson": "When a shopper types a card number into Aurora's checkout, that number never touches your server... This swap is called [[Aurora/_glossary#Tokenization|tokenization]].",
  "quiz": {
    "score": "1/1",
    "rows": [
      { "question": "Where does the real card number go?", "result": "Correct" }
    ]
  }
}
```
