# alexandria-recall

Memory layer. Before anything gets (re-)taught, runs `scripts/recall.py search` over the **current project's** vault folder — frontmatter concepts, glossary, note titles — and surfaces prior sessions so `alexandria-teach` links (`you covered this in [[session]]`) instead of re-teaching. Retrieval never opens other projects' folders by default.

Token cost of a retrieval pass: [references/token-cost.md](references/token-cost.md).

Cross-project references are restricted to two paths (ROADMAP 4.2): an explicit user request, or an exact `_Concepts/` index match — and the latter is announced and permission-gated before anything is imported. Enforced mechanically: `recall.py concept-check` reads only the vault-root concept index, and `recall.py cross-project` (the only command that opens other projects' files) is run strictly after the user says yes.

Drift detection (ROADMAP 4.3) lands next.
