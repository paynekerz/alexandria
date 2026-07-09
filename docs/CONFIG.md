# Alexandria Config — `~/.alexandria/config.json`

One config file, shared by all three skills. Written by the first-run setup interview (Phase 1.1, `scripts/setup.py`); read through a single shared path (§3). If the file is absent, any Alexandria skill runs the setup interview before doing anything else.

## 1. Field reference

| Field | Type | Default | Validation |
|---|---|---|---|
| `vaultPath` | string | `"~/Desktop/Alexandria"` | Expands (`~`, env vars) to an absolute path. Must be writable (created if missing). Must not be inside any `.git` directory. Must not be a file. |
| `preferredModel` | string | `"sonnet"` | Non-empty. Passed verbatim into the teacher subagent's `model` frontmatter (see docs/MODEL-SELECTION.md). Recommended values: `sonnet`, `opus`, `haiku`, `inherit`, or a full model ID like `claude-sonnet-5`. Not validated against a live model list — Claude Code reports invalid models itself. |
| `defaultDepth` | string | `"intro"` | Exactly one of `"intro"`, `"practitioner"`, `"deep-dive"`. Any session can override it; this is only the default. |
| `quizEnabled` | boolean | `false` | Must be JSON `true`/`false`. Opt-in by design (Decision 11): the end-of-session quiz runs only when this is `true` or the user asks for it in-session. |
| `tier1Sources` | object[] | see §2 | Array of `{name, url, scope}` objects. `name` non-empty string; `url` an `https://` URL or the literal `"official-docs"` sentinel; `scope` one of `"general"`, `"algorithms"`, `"video"`. Users may append entries; the defaults should not be removed without understanding Decision 7. |
| `schemaVersion` | integer | `1` | Must equal the config schema version the tooling expects (currently `1`). Mismatch → skills refuse to proceed and point to migration. Note: this versions the **config file**; the vault carries its own `schemaVersion` in `.alexandria/meta.json`. |

Unknown fields are preserved on rewrite but ignored. Missing required fields or failed validation → the skill reports exactly which field is invalid and offers to re-run setup; it never guesses a value.

## 2. Default config (written by setup when the user accepts all defaults)

```json
{
  "schemaVersion": 1,
  "vaultPath": "~/Desktop/Alexandria",
  "preferredModel": "sonnet",
  "defaultDepth": "intro",
  "quizEnabled": false,
  "tier1Sources": [
    { "name": "MIT OpenCourseWare", "url": "https://ocw.mit.edu", "scope": "general" },
    { "name": "Harvard Professional & Lifelong Learning (free catalog)", "url": "https://pll.harvard.edu/catalog/free", "scope": "general" },
    { "name": "Stanford Online", "url": "https://online.stanford.edu", "scope": "general" },
    { "name": "Official language/framework documentation", "url": "official-docs", "scope": "general" },
    { "name": "LeetCode", "url": "https://leetcode.com", "scope": "algorithms" },
    { "name": "MIT OpenCourseWare (YouTube)", "url": "https://www.youtube.com/@mitocw", "scope": "video" },
    { "name": "freeCodeCamp (YouTube)", "url": "https://www.youtube.com/@freecodecamp", "scope": "video" },
    { "name": "Computerphile (YouTube)", "url": "https://www.youtube.com/@Computerphile", "scope": "video" },
    { "name": "3Blue1Brown (YouTube)", "url": "https://www.youtube.com/@3blue1brown", "scope": "video" }
  ]
}
```

Notes on the defaults:

- `"official-docs"` is a sentinel, not a URL: it means "the official documentation site for the language/framework of the concept at hand" (php.net, docs.python.org, developer.mozilla.org, dev.docs for the framework, etc.), resolved per concept by `references/sources.md` rules. It can't be a fixed URL because the right docs site depends on what's being taught.
- `scope` controls when an entry is consulted: `algorithms` entries only for algorithm/data-structure concepts (LeetCode links go to problems and explore cards, never paywalled solutions); `video` entries only when a visual/lecture treatment genuinely adds value.
- **Users may extend this list** — append an object with `name`, `url`, `scope`. Everything in `tier1Sources` is searched before any Tier 2 (open web) fallback.
- Being listed here does not exempt a link from verification: every specific URL is fetched and confirmed alive before it enters a note, defaults included.

## 3. The single shared read path

All config reads go through **`scripts/config.py`** (lands in Phase 1.1 alongside `setup.py`). No skill, script, or subagent parses `~/.alexandria/config.json` on its own.

- **Scripts** import it: `from config import load_config` — returns the validated config dict with `vaultPath` already expanded to an absolute path, or raises `ConfigError` naming the invalid/missing field. `scripts/setup.py` and `scripts/vault.py` both consume this.
- **Skills** shell out to it: `python scripts/config.py` prints the validated, expanded config as JSON to stdout (exit 0), or an error naming the problem (exit 1: file missing → run setup; exit 2: file invalid → the named field). Every SKILL.md's first step is this call; exit 1 is the trigger for the first-run interview.

This gives one place where defaults, expansion, and validation live, so the three skills can never drift apart on how config is interpreted.

## 4. Location

- Path: `~/.alexandria/config.json` (`%USERPROFILE%\.alexandria\config.json` on Windows).
- Created by `scripts/setup.py` with the interview answers merged over the defaults in §2.
- Hand-editing is allowed; the next skill invocation validates and reports any mistake by field name.
