"""Alexandria config — the single shared read path (docs/CONFIG.md section 3).

Scripts import load_config(); skills shell out to `python scripts/config.py`.
Nothing else may parse ~/.alexandria/config.json.

Exit codes (CLI): 0 ok, 1 config missing (run setup), 2 config invalid.
"""
import json
import os
import sys
from pathlib import Path

CONFIG_SCHEMA_VERSION = 1
DEPTHS = ("intro", "practitioner", "deep-dive")
SOURCE_SCOPES = ("general", "algorithms", "video")

DEFAULT_TIER1_SOURCES = [
    {"name": "MIT OpenCourseWare", "url": "https://ocw.mit.edu", "scope": "general"},
    {"name": "Harvard Professional & Lifelong Learning (free catalog)", "url": "https://pll.harvard.edu/catalog/free", "scope": "general"},
    {"name": "Stanford Online", "url": "https://online.stanford.edu", "scope": "general"},
    {"name": "Official language/framework documentation", "url": "official-docs", "scope": "general"},
    {"name": "LeetCode", "url": "https://leetcode.com", "scope": "algorithms"},
    {"name": "MIT OpenCourseWare (YouTube)", "url": "https://www.youtube.com/@mitocw", "scope": "video"},
    {"name": "freeCodeCamp (YouTube)", "url": "https://www.youtube.com/@freecodecamp", "scope": "video"},
    {"name": "Computerphile (YouTube)", "url": "https://www.youtube.com/@Computerphile", "scope": "video"},
    {"name": "3Blue1Brown (YouTube)", "url": "https://www.youtube.com/@3blue1brown", "scope": "video"},
]

DEFAULTS = {
    "schemaVersion": CONFIG_SCHEMA_VERSION,
    "vaultPath": "~/Desktop/Alexandria",
    "preferredModel": "sonnet",
    "defaultDepth": "intro",
    "quizEnabled": False,
    "tier1Sources": DEFAULT_TIER1_SOURCES,
}


class ConfigError(Exception):
    """Invalid config; message names the offending field."""


def config_dir():
    # ALEXANDRIA_CONFIG_DIR is the test hook; real installs use ~/.alexandria
    override = os.environ.get("ALEXANDRIA_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".alexandria"


def config_path():
    return config_dir() / "config.json"


def expand_path(raw):
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def _validate_vault_path(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError("vaultPath: must be a non-empty string")
    expanded = expand_path(raw)
    if expanded.is_file():
        raise ConfigError(f"vaultPath: {expanded} is a file, not a directory")
    if ".git" in expanded.parts:
        raise ConfigError(f"vaultPath: {expanded} is inside a .git directory")
    return expanded


def _validate_tier1_sources(sources):
    if not isinstance(sources, list) or not sources:
        raise ConfigError("tier1Sources: must be a non-empty array")
    for i, entry in enumerate(sources):
        if not isinstance(entry, dict):
            raise ConfigError(f"tier1Sources[{i}]: must be an object")
        name, url, scope = entry.get("name"), entry.get("url"), entry.get("scope")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(f"tier1Sources[{i}].name: must be a non-empty string")
        if not isinstance(url, str) or not (url.startswith("https://") or url == "official-docs"):
            raise ConfigError(f"tier1Sources[{i}].url: must be an https:// URL or 'official-docs'")
        if scope not in SOURCE_SCOPES:
            raise ConfigError(f"tier1Sources[{i}].scope: must be one of {SOURCE_SCOPES}")


def load_config():
    """Return the validated config dict with vaultPath expanded to an absolute path.

    Raises FileNotFoundError if the config file is absent (caller runs setup),
    ConfigError naming the field if any value is invalid.
    """
    path = config_path()
    if not path.is_file():
        raise FileNotFoundError(str(path))
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"config.json: not valid JSON ({e})")
    if not isinstance(cfg, dict):
        raise ConfigError("config.json: top level must be an object")

    if cfg.get("schemaVersion") != CONFIG_SCHEMA_VERSION:
        raise ConfigError(
            f"schemaVersion: expected {CONFIG_SCHEMA_VERSION}, found {cfg.get('schemaVersion')!r} — run scripts/migrate.py"
        )
    cfg["vaultPath"] = str(_validate_vault_path(cfg.get("vaultPath")))
    model = cfg.get("preferredModel")
    if not isinstance(model, str) or not model.strip():
        raise ConfigError("preferredModel: must be a non-empty string")
    if cfg.get("defaultDepth") not in DEPTHS:
        raise ConfigError(f"defaultDepth: must be one of {DEPTHS}")
    if not isinstance(cfg.get("quizEnabled"), bool):
        raise ConfigError("quizEnabled: must be true or false")
    _validate_tier1_sources(cfg.get("tier1Sources"))
    return cfg


def main():
    try:
        cfg = load_config()
    except FileNotFoundError as e:
        print(f"No Alexandria config at {e} — run the first-run setup (scripts/setup.py).", file=sys.stderr)
        return 1
    except ConfigError as e:
        print(f"Invalid Alexandria config: {e}", file=sys.stderr)
        return 2
    json.dump(cfg, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
