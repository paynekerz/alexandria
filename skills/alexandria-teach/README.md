# alexandria-teach

Explanation engine. Reads the code in question, establishes what it does, where it's used, and how it fits the larger architecture, then teaches it at the session's depth (`intro` default; `practitioner`, `deep-dive`). Before explaining anything it checks the project's library through `scripts/recall.py`, so already-taught concepts arrive as `[[wiki-links]]` instead of re-explanations.

Heavy explanation work is delegated to the model-pinned `alexandria-teacher` subagent (see docs/MODEL-SELECTION.md). Every response ends with a save offer and the session's draft concept list; saving is `alexandria-librarian`'s job.

Accuracy rules are non-negotiable: claims about code trace to code read this session, claims about external facts trace to sources fetched and verified this session, and everything else is named as unverifiable rather than guessed.

Reference files (loaded on demand): [references/depth.md](references/depth.md), [references/sources.md](references/sources.md), [references/diagrams.md](references/diagrams.md), [references/quiz.md](references/quiz.md).
