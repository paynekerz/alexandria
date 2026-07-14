# alexandria-recall

Memory layer. Before anything gets (re-)taught, runs `scripts/recall.py search` over the **current project's** vault folder — frontmatter concepts, glossary, note titles — and surfaces prior sessions so `alexandria-teach` links (`you covered this in [[session]]`) instead of re-teaching. Retrieval never opens other projects' folders by default.

Token cost of a retrieval pass: [references/token-cost.md](references/token-cost.md).

Cross-project references (ROADMAP 4.2) and drift detection (ROADMAP 4.3) land next.
