"""Alexandria first-run setup (ROADMAP 1.1).

The skill conducts the interview conversationally, then calls this script
non-interactively with the answers. This script does the deterministic work:
write ~/.alexandria/config.json and scaffold the empty vault.

Exit codes: 0 ok, 2 invalid arguments/paths, 3 already configured (no --force).
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

from config import (
    DEFAULTS,
    DEPTHS,
    ConfigError,
    _validate_vault_path,
    config_path,
    load_config,
)

GENERATOR_VERSION = "0.1.0"

REPO_ROOT = Path(__file__).resolve().parent.parent


def agents_dir():
    # ALEXANDRIA_AGENTS_DIR is the test hook; real installs use ~/.claude/agents
    override = os.environ.get("ALEXANDRIA_AGENTS_DIR")
    return Path(override) if override else Path.home() / ".claude" / "agents"


def generate_teacher_agent(model):
    """Fill agents/alexandria-teacher.md's model placeholder and install it.

    'inherit' means: omit the model line entirely so the subagent runs on
    whatever model the session runs on (see docs/MODEL-SELECTION.md).
    """
    template = (REPO_ROOT / "agents" / "alexandria-teacher.md").read_text(encoding="utf-8")
    if model == "inherit":
        filled = template.replace("model: {{ALEXANDRIA_MODEL}}\n", "")
    else:
        filled = template.replace("{{ALEXANDRIA_MODEL}}", model)
    target = agents_dir() / "alexandria-teacher.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(filled, encoding="utf-8")
    return target


def write_config(vault_path_raw, model, depth, quiz):
    cfg = dict(DEFAULTS)
    cfg.update(
        {
            "vaultPath": vault_path_raw,
            "preferredModel": model,
            "defaultDepth": depth,
            "quizEnabled": quiz,
        }
    )
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return path


def scaffold_vault(vault_root):
    """Create the empty vault per docs/VAULT-SCHEMA.md section 1. Idempotent; never clobbers."""
    created = []
    for d in (vault_root, vault_root / "_Concepts", vault_root / ".alexandria"):
        if not d.exists():
            d.mkdir(parents=True)
            created.append(d)

    meta = vault_root / ".alexandria" / "meta.json"
    if not meta.exists():
        meta.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "createdAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                    "generator": "alexandria",
                    "generatorVersion": GENERATOR_VERSION,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        created.append(meta)

    welcome = vault_root / "Welcome.md"
    if not welcome.exists():
        template = Path(__file__).resolve().parent.parent / "templates" / "Welcome.md"
        welcome.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        created.append(welcome)
    return created


def main():
    parser = argparse.ArgumentParser(description="Write Alexandria config and scaffold the vault.")
    parser.add_argument("--vault-path", default=DEFAULTS["vaultPath"], help="vault location (default: %(default)s)")
    parser.add_argument("--model", default=DEFAULTS["preferredModel"], help="preferred model (default: %(default)s)")
    parser.add_argument("--depth", default=DEFAULTS["defaultDepth"], choices=DEPTHS)
    parser.add_argument("--quiz", default="off", choices=("on", "off"))
    parser.add_argument("--force", action="store_true", help="overwrite an existing config")
    args = parser.parse_args()

    if config_path().is_file() and not args.force:
        print(f"Already configured: {config_path()} exists. Use --force to overwrite.", file=sys.stderr)
        return 3

    if not args.model.strip():
        print("--model must be non-empty", file=sys.stderr)
        return 2
    try:
        vault_root = _validate_vault_path(args.vault_path)
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        return 2

    cfg_file = write_config(args.vault_path, args.model.strip(), args.depth, args.quiz == "on")
    try:
        created = scaffold_vault(vault_root)
    except OSError as e:
        cfg_file.unlink()  # don't leave a config pointing at a vault we couldn't create
        print(f"vaultPath: could not scaffold vault at {vault_root} ({e})", file=sys.stderr)
        return 2
    load_config()  # self-check: what we wrote must pass the shared validator
    agent_file = generate_teacher_agent(args.model.strip())

    print(f"Config written: {cfg_file}")
    print(f"Vault root:     {vault_root}")
    print(f"Teacher agent:  {agent_file} (model: {args.model.strip()})")
    for c in created:
        print(f"  created {c.relative_to(vault_root) if c != vault_root else '.'}")
    if not created:
        print("  vault already existed — nothing created")
    return 0


if __name__ == "__main__":
    sys.exit(main())
