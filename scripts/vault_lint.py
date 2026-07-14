"""Alexandria vault lint & repair (ROADMAP 3.5).

Validates a vault against docs/VAULT-SCHEMA.md section 9 and reports every
violation, one line each, classified:

    frontmatter   session/derived-file frontmatter breaks the schema
    dead-link     a [[wiki-link]] points at a file or heading that doesn't exist
    glossary      orphaned glossary entry, missing entry, or missing backlink
    drift         _index.md or _Concepts/*.md differs from regeneration
    sources       frontmatter sources[] and body ## Sources disagree, or a URL
                  appears outside ## Sources
    meta          .alexandria/meta.json missing/invalid/wrong schemaVersion

`--repair` rewrites the DERIVED files only — every `_index.md` and the whole
`_Concepts/` set — from session frontmatter (the same renderers vault.py uses
to write them). Authored content (session notes, glossary definitions) is
never touched; findings there must be fixed by the librarian or the user.
Repair refuses to run while any session frontmatter is invalid, because
derived files regenerated from broken frontmatter would launder the damage.

CLI:
    python vault_lint.py [--vault PATH] [--repair]

Exit codes: 0 clean, 1 findings reported (or repair performed), 2 unusable
vault/config.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from config import ConfigError, DEPTHS
from vault import (
    CONCEPT_FIELD_ORDER,
    DATE_RE,
    DERIVED_FIELD_ORDER,
    SESSION_FIELD_ORDER,
    SESSION_REQUIRED,
    VAULT_SCHEMA_VERSION,
    NoteError,
    Vault,
    VaultError,
    concept_map,
    list_projects,
    load_sessions,
    parse_frontmatter,
    parse_glossary,
    render_concept_file,
    render_index,
)

WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")
URL_RE = re.compile(r"https?://\S+")


def finding(kind, path, message):
    return {"kind": kind, "path": str(path), "message": message}


def _session_meta_problems(meta, project, stem):
    problems = []
    for field in SESSION_REQUIRED:
        if field not in meta:
            problems.append(f"missing required field {field!r}")
    for field in meta:
        if field not in SESSION_FIELD_ORDER:
            problems.append(f"unknown field {field!r}")
    if meta.get("project") != project:
        problems.append(f"project {meta.get('project')!r} != containing folder {project!r}")
    if "date" in meta and (not isinstance(meta["date"], str) or not DATE_RE.match(meta["date"])):
        problems.append(f"date {meta.get('date')!r} is not YYYY-MM-DD")
    if "date" in meta and isinstance(meta["date"], str) and not stem.startswith(meta["date"]):
        problems.append(f"filename does not start with date {meta['date']!r}")
    if "depth" in meta and meta["depth"] not in DEPTHS:
        problems.append(f"depth {meta.get('depth')!r} not in {DEPTHS}")
    if "concepts" in meta and (not isinstance(meta["concepts"], list) or not meta["concepts"]):
        problems.append("concepts must be a non-empty list")
    for field in ("files", "sources"):
        if field in meta and not isinstance(meta[field], list):
            problems.append(f"{field} must be a list")
    if "commit" in meta and (not isinstance(meta["commit"], str) or not meta["commit"].strip()):
        problems.append("commit must be a non-empty string")
    if "quizScore" in meta and not re.match(r"^\d+/\d+$", str(meta["quizScore"])):
        problems.append(f"quizScore {meta['quizScore']!r} is not '<correct>/<asked>'")
    if "supersedes" in meta and (not isinstance(meta["supersedes"], str) or not meta["supersedes"].strip()):
        problems.append("supersedes must be a non-empty session filename stem")
    if meta.get("schemaVersion") != VAULT_SCHEMA_VERSION:
        problems.append(f"schemaVersion {meta.get('schemaVersion')!r} != {VAULT_SCHEMA_VERSION}")
    return problems


def _derived_meta_problems(meta, project):
    problems = []
    if meta.get("project") != project:
        problems.append(f"project {meta.get('project')!r} != containing folder {project!r}")
    if meta.get("schemaVersion") != VAULT_SCHEMA_VERSION:
        problems.append(f"schemaVersion {meta.get('schemaVersion')!r} != {VAULT_SCHEMA_VERSION}")
    return problems


class Linter:
    def __init__(self, vault):
        self.vault = vault
        self.findings = []
        self.projects = list_projects(vault)
        self.sessions = {}          # project -> [{stem, meta, body}] (parseable notes only)
        self.frontmatter_broken = False

    def add(self, kind, path, message):
        self.findings.append(finding(kind, path, message))

    def run(self):
        self.check_meta_json()
        self.load_all_sessions()
        self.check_session_frontmatter()
        self.check_glossaries()
        self.check_index_drift()
        self.check_concept_drift()
        self.check_sources()
        self.check_wikilinks()
        return self.findings

    # -- meta (invariant 8) --
    def check_meta_json(self):
        meta_file = self.vault.root / ".alexandria" / "meta.json"
        if not meta_file.is_file():
            self.add("meta", ".alexandria/meta.json", "missing")
            return
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            self.add("meta", ".alexandria/meta.json", f"not valid JSON ({e})")
            return
        if meta.get("schemaVersion") != VAULT_SCHEMA_VERSION:
            self.add("meta", ".alexandria/meta.json",
                     f"schemaVersion {meta.get('schemaVersion')!r} != {VAULT_SCHEMA_VERSION} — run scripts/migrate.py")

    def load_all_sessions(self):
        for project in self.projects:
            good = []
            sessions_dir = self.vault.root / project / "Sessions"
            for path in sorted(sessions_dir.glob("*.md")) if sessions_dir.is_dir() else []:
                rel = f"{project}/Sessions/{path.name}"
                try:
                    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
                    good.append({"stem": path.stem, "meta": meta, "body": body})
                except NoteError as e:
                    self.add("frontmatter", rel, str(e))
                    self.frontmatter_broken = True
            self.sessions[project] = good
            # session notes must live under Sessions/ — anything .md loose in
            # the project folder besides the two derived files is a violation
            for stray in sorted((self.vault.root / project).glob("*.md")):
                if stray.name not in ("_glossary.md", "_index.md"):
                    self.add("frontmatter", f"{project}/{stray.name}",
                             "session notes must live under Sessions/")

    # -- invariant 1 + 2 --
    def check_session_frontmatter(self):
        for project, sessions in self.sessions.items():
            stems = {s["stem"] for s in sessions}
            for s in sessions:
                rel = f"{project}/Sessions/{s['stem']}.md"
                for problem in _session_meta_problems(s["meta"], project, s["stem"]):
                    self.add("frontmatter", rel, problem)
                    self.frontmatter_broken = True
                sup = s["meta"].get("supersedes")
                if isinstance(sup, str) and sup.strip() and (sup == s["stem"] or sup not in stems):
                    self.add("dead-link", rel,
                             f"supersedes {sup!r} — no such predecessor session in {project}/Sessions")

    # -- invariant 3: glossary <-> sessions, both directions --
    def check_glossaries(self):
        for project in self.projects:
            rel = f"{project}/_glossary.md"
            path = self.vault.root / project / "_glossary.md"
            taught = {}  # concept -> [stems]
            for s in self.sessions[project]:
                for c in s["meta"].get("concepts", []) if isinstance(s["meta"].get("concepts"), list) else []:
                    taught.setdefault(c, []).append(s["stem"])
            if not path.is_file():
                if taught:
                    self.add("glossary", rel, "missing but project has sessions with concepts")
                continue
            try:
                meta, entries = parse_glossary(path.read_text(encoding="utf-8"))
            except NoteError as e:
                self.add("frontmatter", rel, str(e))
                continue
            for problem in _derived_meta_problems(meta, project):
                self.add("frontmatter", rel, problem)
            for concept, stems in taught.items():
                if concept not in entries:
                    self.add("glossary", rel, f"concept {concept!r} taught in sessions but has no entry")
                    continue
                for stem in stems:
                    if stem not in entries[concept]["sessions"]:
                        self.add("glossary", rel, f"entry {concept!r} does not link back to [[{stem}]]")
            for concept, entry in entries.items():
                if concept not in taught:
                    self.add("glossary", rel, f"orphaned entry {concept!r} — no session in this project teaches it")
                if not entry["definition"]:
                    self.add("glossary", rel, f"entry {concept!r} has an empty definition")

    # -- invariant 4 --
    def check_index_drift(self):
        for project in self.projects:
            rel = f"{project}/_index.md"
            path = self.vault.root / project / "_index.md"
            expected = render_index(project, self.sessions[project])
            if not path.is_file():
                self.add("drift", rel, "missing — regenerable with --repair")
            elif path.read_text(encoding="utf-8") != expected:
                self.add("drift", rel, "differs from regeneration from frontmatter — fix with --repair")

    # -- invariant 6 --
    def check_concept_drift(self):
        cmap = {c: per for c, per in concept_map(self.vault).items() if len(per) >= 2}
        concepts_dir = self.vault.root / "_Concepts"
        existing = {p.stem: p for p in sorted(concepts_dir.glob("*.md"))} if concepts_dir.is_dir() else {}
        for concept, per_project in sorted(cmap.items()):
            rel = f"_Concepts/{concept}.md"
            if concept not in existing:
                self.add("drift", rel, "concept spans 2+ projects but file is missing — fix with --repair")
            elif existing[concept].read_text(encoding="utf-8") != render_concept_file(concept, per_project):
                self.add("drift", rel, "differs from regeneration from frontmatter — fix with --repair")
        for stem in existing:
            if stem not in cmap:
                self.add("drift", f"_Concepts/{stem}.md",
                         "exists but concept is not taught in 2+ projects — removed by --repair")

    # -- invariant 7 --
    def check_sources(self):
        for project, sessions in self.sessions.items():
            for s in sessions:
                rel = f"{project}/Sessions/{s['stem']}.md"
                body = s["body"]
                match = re.search(r"^## Sources\n(.*?)(?=^## |\Z)", body, re.M | re.S)
                section = match.group(1) if match else ""
                section_urls = set(re.findall(r"\((https?://[^)]+)\)", section))
                declared = s["meta"].get("sources", [])
                declared = declared if isinstance(declared, list) else []
                for url in declared:
                    if url not in section_urls:
                        self.add("sources", rel, f"frontmatter source {url} missing from ## Sources")
                outside = body[:match.start()] + body[match.end():] if match else body
                for url in URL_RE.findall(outside):
                    self.add("sources", rel, f"URL outside ## Sources: {url.rstrip('.,)')}")

    # -- invariant 5 --
    def check_wikilinks(self):
        # every .md path (extension dropped) is linkable by full path or bare stem
        by_path, by_stem = {}, {}
        for path in sorted(self.vault.root.rglob("*.md")):
            if ".alexandria" in path.parts:
                continue
            rel_no_ext = path.relative_to(self.vault.root).with_suffix("").as_posix()
            by_path[rel_no_ext] = path
            by_stem.setdefault(path.stem, path)
        for path in sorted(self.vault.root.rglob("*.md")):
            if ".alexandria" in path.parts:
                continue
            rel = path.relative_to(self.vault.root).as_posix()
            for raw in WIKILINK_RE.findall(path.read_text(encoding="utf-8")):
                target, _, heading = raw.partition("#")
                target = target.strip()
                target_path = by_path.get(target) or by_stem.get(target) or (path if not target else None)
                if target_path is None:
                    self.add("dead-link", rel, f"[[{raw}]] — no note named {target!r}")
                    continue
                if heading:
                    text = target_path.read_text(encoding="utf-8")
                    if not re.search(rf"^#{{1,6}} {re.escape(heading.strip())}\s*$", text, re.M):
                        self.add("dead-link", rel, f"[[{raw}]] — {target_path.name} has no heading {heading.strip()!r}")


def repair(vault, linter):
    """Regenerate every derived file from frontmatter. Authored files untouched."""
    if linter.frontmatter_broken:
        raise VaultError(
            "repair refused: session frontmatter errors present — regenerating "
            "derived files from broken frontmatter would spread the damage. Fix "
            "the frontmatter findings first."
        )
    actions = []
    for project in linter.projects:
        actions.append(f"regenerated {vault.write_note(f'{project}/_index.md', render_index(project, load_sessions(vault, project)))}")
    cmap = {c: per for c, per in concept_map(vault).items() if len(per) >= 2}
    for concept, per_project in sorted(cmap.items()):
        actions.append(f"regenerated {vault.write_note(f'_Concepts/{concept}.md', render_concept_file(concept, per_project))}")
    concepts_dir = vault.root / "_Concepts"
    for path in sorted(concepts_dir.glob("*.md")) if concepts_dir.is_dir() else []:
        if path.stem not in cmap:
            actions.append(f"removed     {vault.remove_note(f'_Concepts/{path.name}')}")
    return actions


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lint an Alexandria vault against the v1 schema.")
    parser.add_argument("--vault", help="vault root (default: vaultPath from ~/.alexandria/config.json)")
    parser.add_argument("--repair", action="store_true", help="regenerate derived files (_index.md, _Concepts/)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(errors="replace")

    try:
        vault = Vault(args.vault) if args.vault else Vault.from_config()
    except FileNotFoundError:
        print("No Alexandria config — pass --vault or run scripts/setup.py.", file=sys.stderr)
        return 2
    except (ConfigError, VaultError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if not vault.root.is_dir():
        print(f"vault root {vault.root} does not exist", file=sys.stderr)
        return 2

    linter = Linter(vault)
    findings = linter.run()
    for f in findings:
        print(f"{f['kind']:<11} {f['path']}: {f['message']}")

    if args.repair:
        try:
            for action in repair(vault, linter):
                print(action)
        except VaultError as e:
            print(str(e), file=sys.stderr)
            return 2
        return 1 if findings else 0

    if findings:
        print(f"\n{len(findings)} finding(s).")
        return 1
    print("clean: 0 findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
