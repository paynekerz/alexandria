"""Alexandria recall — read-only retrieval over the vault (ROADMAP 4.1).

`search` scans exactly ONE project's folder: session frontmatter (concepts,
titles) and the project glossary (headings + definitions). It never opens
another project's folder — the current-project default scope (docs/DECISIONS.md
#4) is enforced here, not by skill prose. Output is compact JSON so the model
reads a summary, never raw vault files (Axiom 2).

Cross-project access (ROADMAP 4.2) is split so restraint is mechanical:
`concept-check` consults ONLY the vault-root `_Concepts/` index (exact
filename match — never a fuzzy search, never a project folder) to learn
whether another project teaches a concept; `cross-project` actually reads
the other projects' glossaries and is run only after the user explicitly
asked for cross-project material or granted permission when the skill
announced a concept-index match.

`drift` (ROADMAP 4.3) compares every session's stored commit + files[]
against the repo's current git state (committed AND working-tree changes) and
classifies each: fresh, stale (a covered file changed — offer a refresh),
superseded (a newer note carries `supersedes` naming it), or unverifiable
(no commit to compare — reported honestly, never guessed; Axiom 3).

CLI:
    python recall.py search <Project> --query "<topic words>" [--vault PATH]
    python recall.py concept-check <Project> --concepts "<A,B,...>" [--vault PATH]
    python recall.py cross-project <Project> --concept "<Concept>" [--vault PATH]
    python recall.py drift <Project> --repo <path> [--vault PATH]

Exit codes: 0 ok (including zero matches), 1 config problem, 2 bad usage or
unreadable vault/notes.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from config import ConfigError
from vault import (
    NoteError,
    Vault,
    VaultError,
    list_projects,
    load_sessions,
    parse_frontmatter,
    parse_glossary,
)

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


def concept_check(vault, project, concepts):
    """Exact `_Concepts/<Concept>.md` lookups only — the one signal allowed to
    suggest a cross-project reference without the user asking (ROADMAP 4.2b).
    Reads nothing under any project folder."""
    concepts_dir = vault.resolve("_Concepts")
    # directory listing, not exists(): Windows would match case-insensitively,
    # but canonical concept names are exact (docs/VAULT-SCHEMA.md section 2)
    indexed = {p.stem for p in concepts_dir.glob("*.md")} if concepts_dir.is_dir() else set()
    checked, matches = [], []
    for name in concepts:
        name = name.strip()
        if not name:
            continue
        checked.append(name)
        if name not in indexed:
            continue
        rel = f"_Concepts/{name}.md"
        try:
            meta = parse_frontmatter(vault.read_note(rel))[0]
        except NoteError as e:
            raise RecallError(f"unreadable concept index {rel} — fix it (vault_lint.py) first: {e}")
        others = [p for p in meta.get("projects", []) if p != project]
        if others:
            matches.append({"concept": name, "file": rel, "otherProjects": others})
    return {"project": project, "checked": checked, "matches": matches}


def cross_project(vault, project, concept):
    """The import path — reads OTHER projects' glossaries. Only ever run after
    the user explicitly asked for cross-project material, or said yes when the
    skill announced a concept-check match (ROADMAP 4.2)."""
    concepts_dir = vault.resolve("_Concepts")
    indexed = {p.stem for p in concepts_dir.glob("*.md")} if concepts_dir.is_dir() else set()
    if concept not in indexed:
        raise RecallError(
            f"no cross-project concept index for {concept!r} — nothing to import "
            f"(the index requires an exact match on the canonical concept name)"
        )
    rel = f"_Concepts/{concept}.md"
    try:
        meta, body = parse_frontmatter(vault.read_note(rel))
    except NoteError as e:
        raise RecallError(f"unreadable concept index {rel} — fix it (vault_lint.py) first: {e}")
    imported = []
    for other in meta.get("projects", []):
        if other == project:
            continue
        entry = None
        g_rel = f"{other}/_glossary.md"
        if vault.exists(g_rel):
            try:
                entry = parse_glossary(vault.read_note(g_rel))[1].get(concept)
            except NoteError as e:
                raise RecallError(f"unreadable glossary {g_rel} — fix it (vault_lint.py) first: {e}")
        imported.append({
            "project": other,
            "definition": entry["definition"] if entry else None,
            "sessions": sorted(entry["sessions"]) if entry else [],
        })
    refs_match = re.search(r"^## References\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    references = re.findall(r"\[[^\]]+\]\(https?://[^)]+\)", refs_match.group(1)) if refs_match else []
    return {"project": project, "concept": concept, "importedFrom": imported, "references": references}


def _git(repo, *args):
    try:
        return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    except FileNotFoundError:
        raise RecallError("git is not available on PATH — drift detection cannot run without it")


def drift(vault, project, repo):
    """Stored commit + files[] vs the repo now. Statuses, in decision order:
    superseded > unverifiable (bad/absent commit) > stale (a file differs,
    committed or working-tree) > unverifiable (a file absent from both commit
    and worktree) > fresh."""
    repo = Path(repo).resolve()
    if not repo.is_dir() or _git(repo, "rev-parse", "--is-inside-work-tree").returncode != 0:
        raise RecallError(f"{repo} is not a git repository — drift cannot be verified there (Axiom 3)")
    if project not in list_projects(vault):
        raise RecallError(f"no project folder named {project!r} in {vault.root}")
    try:
        sessions = load_sessions(vault, project)
    except NoteError as e:
        raise RecallError(f"unreadable session note — fix it (vault_lint.py) before drift can run: {e}")

    superseded_by = {}
    for s in sorted(sessions, key=lambda s: (s["meta"]["date"], s["stem"])):
        sup = s["meta"].get("supersedes")
        if isinstance(sup, str) and sup.strip():
            superseded_by[sup] = s["stem"]

    report = []
    for s in sorted(sessions, key=lambda s: (s["meta"]["date"], s["stem"]), reverse=True):
        m, stem = s["meta"], s["stem"]
        entry = {"note": stem, "date": m["date"], "commit": m["commit"]}
        if stem in superseded_by:
            entry.update(status="superseded", supersededBy=superseded_by[stem])
        elif m["commit"] == "unversioned":
            entry.update(status="unverifiable", reason="saved without version control — no commit to compare")
        elif _git(repo, "rev-parse", "--quiet", "--verify", m["commit"] + "^{commit}").returncode != 0:
            entry.update(status="unverifiable", reason=f"stored commit {m['commit']} not found in {repo.name}")
        else:
            changed, missing = [], []
            for f in m.get("files", []):
                r = _git(repo, "diff", "--quiet", m["commit"], "--", f)
                if r.returncode == 1:
                    changed.append(f)
                elif r.returncode != 0:
                    raise RecallError(f"git diff failed for {f!r}: {r.stderr.strip()}")
                elif not (repo / f).exists():
                    missing.append(f)
            if changed:
                entry.update(status="stale", changedFiles=changed)
            elif missing:
                entry.update(status="unverifiable", missingFiles=missing,
                             reason="listed file(s) absent from both the stored commit and the worktree")
            else:
                entry.update(status="fresh")
        report.append(entry)
    return {"project": project, "repo": str(repo), "sessions": report,
            "stale": [e["note"] for e in report if e["status"] == "stale"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only retrieval over an Alexandria vault.")
    parser.add_argument("--vault", help="vault root (default: vaultPath from ~/.alexandria/config.json)")
    sub = parser.add_subparsers(dest="command", required=True)
    p_search = sub.add_parser("search", help="search ONE project's sessions, concepts, and glossary")
    p_search.add_argument("project", help="project folder name (current project)")
    p_search.add_argument("--query", required=True, help="topic words to search for")
    p_check = sub.add_parser("concept-check", help="exact _Concepts/ index lookups; never reads project folders")
    p_check.add_argument("project", help="current project (excluded from results)")
    p_check.add_argument("--concepts", required=True, help="comma-separated canonical concept names")
    p_cross = sub.add_parser("cross-project", help="import one concept's material from other projects (permission-gated)")
    p_cross.add_argument("project", help="current project (excluded from results)")
    p_cross.add_argument("--concept", required=True, help="canonical concept name")
    p_drift = sub.add_parser("drift", help="flag sessions whose covered files changed since their stored commit")
    p_drift.add_argument("project", help="project folder name (current project)")
    p_drift.add_argument("--repo", required=True, help="path to the project's git repository")
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
        elif args.command == "concept-check":
            json.dump(concept_check(vault, args.project, args.concepts.split(",")), sys.stdout, indent=1)
            print()
        elif args.command == "cross-project":
            json.dump(cross_project(vault, args.project, args.concept), sys.stdout, indent=1)
            print()
        elif args.command == "drift":
            json.dump(drift(vault, args.project, args.repo), sys.stdout, indent=1)
            print()
    except (RecallError, VaultError) as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
