"""Alexandria vault I/O — the ONLY module allowed to touch vault files (ROADMAP 1.2).

Every skill and script performs vault filesystem operations through this module.
Hard guarantee: no write ever lands outside the vault root. Paths are fully
resolved (symlinks, `..`, drive changes) and checked against the root before
any filesystem call.

CLI (for skills):
    python vault.py scaffold                      create root/_Concepts/.alexandria/meta.json/Welcome.md
    python vault.py ensure-project <Project>      create <Project>/Sessions
    python vault.py write-note <relative-path>    write stdin to the note, atomically

Exit codes: 0 ok, 1 config problem, 2 path rejected / write failed.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

from config import ConfigError, expand_path, load_config


class VaultError(Exception):
    """Vault operation failed (bad root, unwritable location)."""


class VaultPathError(VaultError):
    """Target path escapes the vault root — always refused, never created."""


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


def main(argv):
    if len(argv) < 2 or argv[1] not in ("scaffold", "ensure-project", "write-note"):
        print(__doc__, file=sys.stderr)
        return 2
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
    except IndexError:
        print("missing argument", file=sys.stderr)
        return 2
    except VaultError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
