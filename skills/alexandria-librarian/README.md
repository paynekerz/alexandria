# alexandria-librarian

Persistence layer. On "save" it confirms the lesson's concept list with the user (the user curates; nothing enters the library unconfirmed), assembles the session payload -- title, depth, files read, commit hash, confirmed concepts with intro-level definitions, verified sources -- and pipes it through `scripts/vault.py save-session`, the single gate for all vault writes.

The script then does the deterministic work: writes the session note with schema v1 frontmatter, merges the project glossary, regenerates `_index.md`, and creates or updates `_Concepts/<Concept>.md` for any concept now taught in 2+ projects. The skill never edits those files by hand; they're script-owned and losslessly regenerable from note frontmatter (`scripts/vault_lint.py --repair`).

Payload format with a worked example: [references/payload.md](references/payload.md).
