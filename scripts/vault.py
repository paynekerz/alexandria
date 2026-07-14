"""Alexandria vault I/O — the ONLY module allowed to touch vault files (ROADMAP 1.2).

Every skill and script performs vault filesystem operations through this module.
Hard guarantee: no write ever lands outside the vault root. Paths are fully
resolved (symlinks, `..`, drive changes) and checked against the root before
any filesystem call.

CLI (for skills):
    python vault.py scaffold                      create root/_Concepts/.alexandria/meta.json/Welcome.md
    python vault.py ensure-project <Project>      create <Project>/Sessions
    python vault.py write-note <relative-path>    write stdin to the note, atomically
    python vault.py save-session                  full save pipeline (ROADMAP 3.1); JSON payload on stdin
    python vault.py regen-index <Project>         rebuild <Project>/_index.md from session frontmatter
    python vault.py regen-concepts                rebuild _Concepts/*.md for concepts taught in 2+ projects

Exit codes: 0 ok, 1 config problem, 2 path rejected / write failed, 3 vault schemaVersion mismatch.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from config import DEPTHS, ConfigError, expand_path, load_config


class VaultError(Exception):
    """Vault operation failed (bad root, unwritable location)."""


class VaultPathError(VaultError):
    """Target path escapes the vault root — always refused, never created."""


class VaultSchemaError(VaultError):
    """Vault schemaVersion differs from what this Alexandria writes (ROADMAP 3.6)."""


class NoteError(VaultError):
    """Note content or save payload violates docs/VAULT-SCHEMA.md."""


class Vault:
    def __init__(self, root):
        root = expand_path(str(root))
        if ".git" in root.parts:
            raise VaultError(f"vault root {root} is inside a .git directory")
        if root.is_file():
            raise VaultError(f"vault root {root} is a file, not a directory")
        self.root = root

    @classmethod
    def from_config(cls):
        """Resolve the vault from the single shared config read path."""
        return cls(load_config()["vaultPath"])

    def resolve(self, relative):
        """Resolve a vault-relative path, refusing anything outside the root.

        This is the enforcement point for the no-writes-outside-root guarantee:
        every public method funnels through it before touching the filesystem.
        """
        rel = str(relative)
        p = Path(rel)
        if p.is_absolute() or (len(rel) > 1 and rel[1] == ":"):
            raise VaultPathError(f"absolute paths are not allowed: {rel}")
        # resolve() collapses `..` and follows symlinks, so a crafted relative
        # path can't sneak out and a symlink inside the vault can't point out.
        candidate = (self.root / p).resolve()
        root = self.root.resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            raise VaultPathError(f"{rel} escapes the vault root {root}")
        return candidate

    def ensure_root(self):
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise VaultError(f"vault root {self.root} is not writable: {e}")
        return self.root

    def ensure_dir(self, relative):
        target = self.resolve(relative)
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise VaultError(f"cannot create {target}: {e}")
        return target

    def ensure_project(self, project):
        if project.startswith((".", "_")):
            raise VaultError(f"project name {project!r} may not start with '.' or '_'")
        return self.ensure_dir(Path(project) / "Sessions")

    def write_note(self, relative, content):
        """Atomic write: temp file in the target directory, then os.replace.

        A crash mid-write leaves the old note intact — the vault never holds a
        half-written file.
        """
        target = self.resolve(relative)
        self.ensure_dir(Path(relative).parent)
        fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            os.replace(tmp, target)
        except OSError as e:
            raise VaultError(f"cannot write {target}: {e}")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return target

    def read_note(self, relative):
        return self.resolve(relative).read_text(encoding="utf-8")

    def exists(self, relative):
        return self.resolve(relative).exists()

    def remove_note(self, relative):
        """Delete a single derived file (lint --repair only). Never a directory."""
        target = self.resolve(relative)
        if target.is_dir():
            raise VaultError(f"refusing to remove a directory: {target}")
        if target.exists():
            target.unlink()
        return target


# --- Note schema (docs/VAULT-SCHEMA.md) -------------------------------------
#
# Everything below implements sections 3-7 of the schema doc. Indexes and
# concept files are DERIVED data: rendered only from session frontmatter (plus
# glossary definitions, which are authored once and never rewritten), so
# vault_lint.py --repair can regenerate them losslessly (ROADMAP 3.3/3.5).

VAULT_SCHEMA_VERSION = 1

SESSION_FIELD_ORDER = (
    "project", "title", "date", "depth", "concepts", "files",
    "commit", "sources", "quizScore", "supersedes", "schemaVersion",
)
SESSION_REQUIRED = (
    "project", "title", "date", "depth", "concepts", "files",
    "commit", "sources", "schemaVersion",
)
DERIVED_FIELD_ORDER = ("project", "schemaVersion")
CONCEPT_FIELD_ORDER = ("concept", "projects", "schemaVersion")
QUOTED_FIELDS = frozenset({"quizScore"})
# characters Obsidian or Windows reject in filenames (schema section 2)
FORBIDDEN_NAME_CHARS = re.compile(r'[\\/:*?"<>|#^\[\]]')
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def parse_frontmatter(text):
    """Parse the fixed v1 frontmatter dialect: scalars, `- ` lists, `[]`.

    Returns (meta dict, body str). Only schemaVersion becomes an int — a
    commit hash that happens to be all digits must stay a string.
    """
    if not text.startswith("---\n"):
        raise NoteError("missing opening '---' frontmatter fence")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise NoteError("missing closing '---' frontmatter fence")
    meta, current_list = {}, None
    for raw in text[4:end].split("\n"):
        if raw.startswith("  - "):
            if current_list is None:
                raise NoteError(f"list item without a list key: {raw!r}")
            meta[current_list].append(raw[4:].strip())
        elif ":" in raw:
            key, _, value = raw.partition(":")
            key, value = key.strip(), value.strip()
            if value == "":
                meta[key], current_list = [], key
            else:
                current_list = None
                if value == "[]":
                    meta[key] = []
                elif key == "schemaVersion" and value.isdigit():
                    meta[key] = int(value)
                elif len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                    meta[key] = value[1:-1]
                else:
                    meta[key] = value
        elif raw.strip():
            raise NoteError(f"unparseable frontmatter line: {raw!r}")
    return meta, text[end + 5:]


def serialize_frontmatter(meta, order):
    lines = ["---"]
    for key in order:
        if key not in meta:
            continue
        value = meta[key]
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {item}" for item in value)
            else:
                lines.append(f"{key}: []")
        elif key in QUOTED_FIELDS:
            lines.append(f'{key}: "{value}"')
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def check_vault_schema(vault):
    """Refuse to write into a vault whose schemaVersion we don't speak (ROADMAP 3.6)."""
    meta_file = vault.resolve(".alexandria/meta.json")
    if not meta_file.is_file():
        raise VaultError(
            f"{vault.root} is not an Alexandria vault (no .alexandria/meta.json) — run 'python vault.py scaffold'"
        )
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise VaultError(f".alexandria/meta.json is not valid JSON ({e})")
    found = meta.get("schemaVersion")
    if found != VAULT_SCHEMA_VERSION:
        raise VaultSchemaError(
            f"vault schemaVersion is {found!r} but this Alexandria writes version {VAULT_SCHEMA_VERSION}. "
            f"No writes performed. Run 'python scripts/migrate.py' to bring the vault up to date."
        )


def list_projects(vault):
    """Project folders only — skips dot-folders and derived folders like _Concepts."""
    return sorted(
        d.name for d in vault.root.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))
    )


def load_sessions(vault, project):
    """All session notes of a project as {stem, meta, body}, filename order."""
    sessions_dir = vault.resolve(Path(project) / "Sessions")
    if not sessions_dir.is_dir():
        return []
    out = []
    for path in sorted(sessions_dir.glob("*.md")):
        try:
            meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        except NoteError as e:
            raise NoteError(f"{project}/Sessions/{path.name}: {e}")
        out.append({"stem": path.stem, "meta": meta, "body": body})
    return out


# --- _index.md (schema section 6) --------------------------------------------

def render_index(project, sessions):
    lines = [
        f"# Index — {project}",
        "",
        "| Date | Session | Depth | Concepts | Files | Commit |",
        "|---|---|---|---|---|---|",
    ]
    for s in sorted(sessions, key=lambda s: (s["meta"]["date"], s["stem"]), reverse=True):
        m = s["meta"]
        lines.append(
            "| {date} | [[{stem}]] | {depth} | {concepts} | {files} | {commit} |".format(
                date=m["date"], stem=s["stem"], depth=m["depth"],
                concepts=", ".join(m["concepts"]), files=", ".join(m["files"]), commit=m["commit"],
            )
        )
    head = serialize_frontmatter(
        {"project": project, "schemaVersion": VAULT_SCHEMA_VERSION}, DERIVED_FIELD_ORDER
    )
    return head + "\n" + "\n".join(lines) + "\n"


def regen_index(vault, project):
    return vault.write_note(f"{project}/_index.md", render_index(project, load_sessions(vault, project)))


# --- _glossary.md (schema section 5) -----------------------------------------

def parse_glossary(text):
    """Returns (meta, {concept: {definition, sessions[]}}). Definitions are
    authored prose — parsed verbatim, never regenerated."""
    meta, body = parse_frontmatter(text)
    entries, name, buf = {}, None, []

    def flush():
        if name is None:
            return
        sessions, definition_lines = [], []
        for line in buf:
            if line.startswith("Sessions: "):
                sessions = re.findall(r"\[\[([^\]|]+)\]\]", line)
            else:
                definition_lines.append(line)
        entries[name] = {"definition": "\n".join(definition_lines).strip(), "sessions": sessions}

    for line in body.split("\n"):
        if line.startswith("## "):
            flush()
            name, buf = line[3:].strip(), []
        elif name is not None:
            buf.append(line)
    flush()
    return meta, entries


def render_glossary(project, entries):
    lines = [f"# Glossary — {project}"]
    for name in sorted(entries, key=str.casefold):
        entry = entries[name]
        lines.extend([
            "", f"## {name}", "", entry["definition"], "",
            "Sessions: " + ", ".join(f"[[{s}]]" for s in sorted(entry["sessions"])),
        ])
    head = serialize_frontmatter(
        {"project": project, "schemaVersion": VAULT_SCHEMA_VERSION}, DERIVED_FIELD_ORDER
    )
    return head + "\n" + "\n".join(lines) + "\n"


def update_glossary(vault, project, stem, concepts):
    """Merge a session's concepts into the project glossary (ROADMAP 3.2).

    New concept -> entry inserted (alphabetical) with the provided definition.
    Existing concept -> its session-link list gains this session; the
    definition is never touched, so re-teaching can't silently rewrite it.
    """
    rel = f"{project}/_glossary.md"
    entries = parse_glossary(vault.read_note(rel))[1] if vault.exists(rel) else {}
    added, linked = [], []
    for concept in concepts:
        name = concept["name"]
        if name in entries:
            if stem not in entries[name]["sessions"]:
                entries[name]["sessions"].append(stem)
                linked.append(name)
        else:
            definition = (concept.get("definition") or "").strip()
            if not definition:
                raise NoteError(f"concept {name!r} is new to {project} and needs an intro-level definition")
            entries[name] = {"definition": definition, "sessions": [stem]}
            added.append(name)
    vault.write_note(rel, render_glossary(project, entries))
    return added, linked


# --- _Concepts/<Concept>.md (schema section 7) --------------------------------

def concept_map(vault):
    """{concept: {project: [sessions date-ascending]}} from frontmatter alone."""
    out = {}
    for project in list_projects(vault):
        for session in load_sessions(vault, project):
            for concept in session["meta"].get("concepts", []):
                out.setdefault(concept, {}).setdefault(project, []).append(session)
    for per_project in out.values():
        for sessions in per_project.values():
            sessions.sort(key=lambda s: (s["meta"]["date"], s["stem"]))
    return out


def _source_link_titles(body):
    """{url: title} for every markdown link under the note's ## Sources section."""
    match = re.search(r"^## Sources\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    if not match:
        return {}
    return {url: title for title, url in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", match.group(1))}


def render_concept_file(concept, per_project):
    projects = sorted(per_project, key=lambda p: (per_project[p][0]["meta"]["date"], p))
    lines = [f"# {concept}", "", f"Taught in {len(projects)} projects."]
    for project in projects:
        lines.extend(["", f"## {project}", "",
                      f"Glossary: [[{project}/_glossary#{concept}|{concept} in {project}]]", ""])
        lines.extend(f"- [[{s['stem']}]]" for s in per_project[project])
    references, seen = [], set()
    every_session = sorted(
        (s for sessions in per_project.values() for s in sessions),
        key=lambda s: (s["meta"]["date"], s["stem"]),
    )
    for session in every_session:
        titles = _source_link_titles(session["body"])
        for url in session["meta"].get("sources", []):
            if url not in seen:
                seen.add(url)
                references.append(f"[{titles[url]}]({url})" if url in titles else url)
    if references:
        lines.extend(["", "## References", ""])
        lines.extend(f"- {ref}" for ref in references)
    head = serialize_frontmatter(
        {"concept": concept, "projects": projects, "schemaVersion": VAULT_SCHEMA_VERSION},
        CONCEPT_FIELD_ORDER,
    )
    return head + "\n" + "\n".join(lines) + "\n"


def regen_concepts(vault, only=None):
    """(Re)write _Concepts/<Concept>.md for every concept taught in 2+ projects.

    Single-project concepts never get a file (schema invariant 6). `only`
    restricts the pass to the concepts a save just touched.
    """
    written = []
    for concept, per_project in sorted(concept_map(vault).items()):
        if only is not None and concept not in only:
            continue
        if len(per_project) >= 2:
            written.append(vault.write_note(f"_Concepts/{concept}.md", render_concept_file(concept, per_project)))
    return written


# --- save-session pipeline (ROADMAP 3.1) --------------------------------------

def _kebab(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise NoteError(f"title {title!r} produces an empty filename slug")
    return slug


def payload_problems(payload):
    """Every schema violation in a save payload, or [] if it is saveable."""
    problems = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]
    for field in ("project", "title", "date", "depth", "commit", "lesson"):
        if not isinstance(payload.get(field), str) or not payload.get(field, "").strip():
            problems.append(f"{field}: required non-empty string")
    project = payload.get("project", "")
    if isinstance(project, str) and project.startswith((".", "_")):
        problems.append("project: may not start with '.' or '_'")
    if isinstance(project, str) and FORBIDDEN_NAME_CHARS.search(project):
        problems.append(r'project: contains a character Obsidian/Windows rejects (\ / : * ? " < > | # ^ [ ])')
    if isinstance(payload.get("date"), str) and not DATE_RE.match(payload["date"]):
        problems.append("date: must be ISO 8601 YYYY-MM-DD")
    if payload.get("depth") not in DEPTHS:
        problems.append(f"depth: must be one of {DEPTHS}")
    concepts = payload.get("concepts")
    if not isinstance(concepts, list) or not concepts:
        problems.append("concepts: required non-empty array of {name, definition} objects")
        concepts = []
    for i, concept in enumerate(concepts):
        name = concept.get("name") if isinstance(concept, dict) else None
        if not isinstance(name, str) or not name.strip():
            problems.append(f"concepts[{i}].name: required non-empty string")
        elif FORBIDDEN_NAME_CHARS.search(name):
            problems.append(f"concepts[{i}].name: {name!r} contains a forbidden filename character")
    files = payload.get("files")
    if not isinstance(files, list) or any(not isinstance(f, str) or not f.strip() for f in files):
        problems.append("files: required array of non-empty strings (may be empty)")
    sources = payload.get("sources")
    if not isinstance(sources, list):
        problems.append("sources: required array of {title, url} objects (may be empty)")
        sources = []
    for i, source in enumerate(sources):
        if not isinstance(source, dict) or not source.get("title") or not str(source.get("url", "")).startswith(("https://", "http://")):
            problems.append(f"sources[{i}]: needs a title and an http(s) url")
    if "slug" in payload and (not isinstance(payload["slug"], str) or not SLUG_RE.match(payload["slug"])):
        problems.append("slug: must be kebab-case (lowercase letters, digits, single dashes)")
    quiz = payload.get("quiz")
    if quiz is not None:
        rows = quiz.get("rows") if isinstance(quiz, dict) else None
        if (not isinstance(quiz, dict) or not re.match(r"^\d+/\d+$", str(quiz.get("score", "")))
                or not isinstance(rows, list) or not rows
                or any(not isinstance(r, dict) or not r.get("question") or not r.get("result") for r in rows)):
            problems.append('quiz: needs {"score": "<correct>/<asked>", "rows": [{"question", "result"}, ...]}')
    lesson = payload.get("lesson", "")
    if isinstance(lesson, str) and isinstance(project, str):
        for concept in concepts:
            name = concept.get("name") if isinstance(concept, dict) else None
            if isinstance(name, str) and f"[[{project}/_glossary#{name}" not in lesson:
                problems.append(
                    f"lesson: first mention of {name!r} must wiki-link the glossary entry "
                    f"([[{project}/_glossary#{name}|...]])"
                )
        if re.search(r"https?://", lesson):
            problems.append("lesson: external URLs belong under sources, never in the lesson prose (schema invariant 7)")
    supersedes = payload.get("supersedes")
    if supersedes is not None:
        if not isinstance(supersedes, str) or not supersedes.strip():
            problems.append("supersedes: must be the predecessor session's filename stem")
        elif isinstance(lesson, str) and f"[[{supersedes}]]" not in lesson:
            problems.append(
                f"lesson: a refresh must link its predecessor in the prose ([[{supersedes}]]) — "
                f"history is preserved, never overwritten (ROADMAP 4.3)"
            )
    return problems


def _render_session_note(payload, concept_names):
    meta = {
        "project": payload["project"],
        "title": payload["title"],
        "date": payload["date"],
        "depth": payload["depth"],
        "concepts": concept_names,
        "files": payload["files"],
        "commit": payload["commit"],
        "sources": [s["url"] for s in payload["sources"]],
        "schemaVersion": VAULT_SCHEMA_VERSION,
    }
    quiz = payload.get("quiz")
    if quiz:
        meta["quizScore"] = quiz["score"]
    if payload.get("supersedes"):
        meta["supersedes"] = payload["supersedes"]
    lines = [f"# {payload['title']}", "", "## Lesson", "", payload["lesson"].strip()]
    if payload["files"]:
        lines.extend(["", "## Files", ""])
        lines.extend(f"- `{path}` @ `{payload['commit']}`" for path in payload["files"])
    if payload["sources"]:
        lines.extend(["", "## Sources", ""])
        lines.extend(f"- [{s['title']}]({s['url']})" for s in payload["sources"])
    if quiz:
        lines.extend(["", "## Comprehension", "", "| # | Question | Result |", "|---|---|---|"])
        lines.extend(f"| {i} | {row['question']} | {row['result']} |" for i, row in enumerate(quiz["rows"], 1))
        lines.extend(["", f"Score: {quiz['score']}"])
    return serialize_frontmatter(meta, SESSION_FIELD_ORDER) + "\n" + "\n".join(lines) + "\n"


def save_session(vault, payload):
    """The one save path (ROADMAP 3.1): note, then glossary, then index, then
    cross-project concept files — every write through Vault, none freehand."""
    problems = payload_problems(payload)
    if problems:
        raise NoteError("payload rejected:\n  " + "\n  ".join(problems))
    check_vault_schema(vault)
    project = payload["project"]
    stem = f"{payload['date']} {payload.get('slug') or _kebab(payload['title'])}"
    rel = f"{project}/Sessions/{stem}.md"
    if vault.exists(rel):
        raise VaultError(f"{rel} already exists — one note per session; pick a different slug")
    supersedes = payload.get("supersedes")
    if supersedes and not vault.exists(f"{project}/Sessions/{supersedes}.md"):
        raise NoteError(
            f"supersedes {supersedes!r}: no such session in {project}/Sessions — "
            f"a refresh must name its existing predecessor"
        )
    vault.ensure_project(project)
    concept_names = [c["name"] for c in payload["concepts"]]
    note_path = vault.write_note(rel, _render_session_note(payload, concept_names))
    added, linked = update_glossary(vault, project, stem, payload["concepts"])
    index_path = regen_index(vault, project)
    concept_paths = regen_concepts(vault, only=set(concept_names))
    return {
        "note": note_path, "glossaryAdded": added, "glossaryLinked": linked,
        "index": index_path, "conceptFiles": concept_paths,
    }


def main(argv):
    commands = ("scaffold", "ensure-project", "write-note", "save-session", "regen-index", "regen-concepts")
    if len(argv) < 2 or argv[1] not in commands:
        print(__doc__, file=sys.stderr)
        return 2
    # Windows defaults stdio to cp1252; note content is always UTF-8
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(errors="replace")
    try:
        vault = Vault.from_config()
    except FileNotFoundError:
        print("No Alexandria config — run scripts/setup.py first.", file=sys.stderr)
        return 1
    except (ConfigError, VaultError) as e:
        print(str(e), file=sys.stderr)
        return 1

    try:
        if argv[1] == "scaffold":
            from setup import scaffold_vault  # shares the one scaffold implementation

            vault.ensure_root()
            created = scaffold_vault(vault.root)
            print(f"ok: {len(created)} item(s) created under {vault.root}")
        elif argv[1] == "ensure-project":
            print(f"ok: {vault.ensure_project(argv[2])}")
        elif argv[1] == "write-note":
            print(f"ok: {vault.write_note(argv[2], sys.stdin.read())}")
        elif argv[1] == "save-session":
            try:
                payload = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                print(f"refused: stdin is not valid JSON ({e})", file=sys.stderr)
                return 2
            result = save_session(vault, payload)
            print(f"note:     {result['note']}")
            glossary_bits = []
            if result["glossaryAdded"]:
                glossary_bits.append("added " + ", ".join(result["glossaryAdded"]))
            if result["glossaryLinked"]:
                glossary_bits.append("linked " + ", ".join(result["glossaryLinked"]))
            print(f"glossary: {'; '.join(glossary_bits) or 'unchanged'}")
            print(f"index:    {result['index']}")
            if result["conceptFiles"]:
                for path in result["conceptFiles"]:
                    print(f"concepts: {path}")
            else:
                print("concepts: none — no saved concept spans 2+ projects")
        elif argv[1] == "regen-index":
            print(f"ok: {regen_index(vault, argv[2])}")
        elif argv[1] == "regen-concepts":
            written = regen_concepts(vault)
            print(f"ok: {len(written)} concept file(s) regenerated")
            for path in written:
                print(f"  {path}")
    except IndexError:
        print("missing argument", file=sys.stderr)
        return 2
    except VaultSchemaError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 3
    except VaultError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
