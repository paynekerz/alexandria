"""Alexandria recall — read-only retrieval over the vault (ROADMAP 4.1).

`search` scans exactly ONE project's folder: session frontmatter (concepts,
titles) and the project glossary (headings + definitions). It never opens
another project's folder — the current-project default scope (docs/DECISIONS.md
#4) is enforced here, not by skill prose. Output is compact JSON so the model
reads a summary, never raw vault files (Axiom 2).

CLI:
    python recall.py search <Project> --query "<topic words>" [--vault PATH]

Exit codes: 0 ok (including zero matches), 1 config problem, 2 bad usage or
unreadable vault/notes.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from config import ConfigError
from vault import NoteError, Vault, VaultError, list_projects, load_sessions, parse_glossary

MIN_TERM_LEN = 3


class RecallError(Exception):
    """Retrieval cannot proceed (bad query, unreadable note)."""


def _words(text):
    return [w for w in re.split(r"[^a-z0-9]+", text.lower()) if len(w) >= MIN_TERM_LEN]


def _terms(query):
    terms = _words(query)
    if not terms:
        raise RecallError(f"query {query!r} has no searchable terms ({MIN_TERM_LEN}+ characters)")
    return terms


def _singular(word):
    return word[:-1] if word.endswith("s") and len(word) > MIN_TERM_LEN else word


def _hit(term, text):
    """A term hits a text when it shares a stem with any of the text's words
    (substring either way, plural-insensitive: 'tokens' hits 'Tokenization',
    'webhooks' hits 'webhook-handling')."""
    t = _singular(term)
    return any(t in v or v in t for w in _words(text) for v in (_singular(w),))


def search(vault, project, query):
    terms = _terms(query)
    if project not in list_projects(vault):
        return {"project": project, "query": query, "projectExists": False,
                "taughtConcepts": [], "sessions": [], "glossary": []}
    try:
        sessions = load_sessions(vault, project)
    except NoteError as e:
        raise RecallError(f"unreadable session note — fix it (vault_lint.py) before recall can search: {e}")

    scored = []
    for s in sessions:
        m = s["meta"]
        matched, hit_terms = [], set()
        for concept in m.get("concepts", []):
            hits = [t for t in terms if _hit(t, concept)]
            if hits:
                matched.append(f"concept: {concept}")
                hit_terms.update(hits)
        title_hits = [t for t in terms if _hit(t, m.get("title", "")) or _hit(t, s["stem"])]
        if title_hits:
            matched.append("title")
            hit_terms.update(title_hits)
        if matched:
            scored.append((len(hit_terms), m["date"], {
                "note": s["stem"], "title": m["title"], "date": m["date"], "depth": m["depth"],
                "matched": matched, "concepts": m["concepts"], "files": m["files"], "commit": m["commit"],
            }))
    scored.sort(key=lambda x: (x[0], x[1], x[2]["note"]), reverse=True)

    taught, glossary_hits = [], []
    rel = f"{project}/_glossary.md"
    if vault.exists(rel):
        try:
            entries = parse_glossary(vault.read_note(rel))[1]
        except NoteError as e:
            raise RecallError(f"unreadable glossary — fix it (vault_lint.py) before recall can search: {e}")
        taught = sorted(entries, key=str.casefold)
        for name in taught:
            entry = entries[name]
            name_hit = any(_hit(t, name) for t in terms)
            if name_hit or any(_hit(t, entry["definition"]) for t in terms):
                glossary_hits.append({
                    "concept": name,
                    "matched": "name" if name_hit else "definition",
                    "sessions": sorted(entry["sessions"]),
                })
    return {"project": project, "query": query, "projectExists": True, "taughtConcepts": taught,
            "sessions": [entry for _, _, entry in scored], "glossary": glossary_hits}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only retrieval over an Alexandria vault.")
    parser.add_argument("--vault", help="vault root (default: vaultPath from ~/.alexandria/config.json)")
    sub = parser.add_subparsers(dest="command", required=True)
    p_search = sub.add_parser("search", help="search ONE project's sessions, concepts, and glossary")
    p_search.add_argument("project", help="project folder name (current project)")
    p_search.add_argument("--query", required=True, help="topic words to search for")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(errors="replace")

    try:
        vault = Vault(args.vault) if args.vault else Vault.from_config()
    except FileNotFoundError:
        print("No Alexandria config — pass --vault or run scripts/setup.py.", file=sys.stderr)
        return 1
    except (ConfigError, VaultError) as e:
        print(str(e), file=sys.stderr)
        return 1
    if not vault.root.is_dir():
        print(f"vault root {vault.root} does not exist", file=sys.stderr)
        return 1

    try:
        if args.command == "search":
            json.dump(search(vault, args.project, args.query), sys.stdout, indent=1)
            print()
    except (RecallError, VaultError) as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
