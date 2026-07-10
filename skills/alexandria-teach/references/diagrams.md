# Diagram rules — Mermaid only

Obsidian renders Mermaid natively (Decision 8). A diagram is a claim about structure — it must earn its place and it must render.

## When a diagram earns its place

Include one only when the explanation has **structural or flow character** that prose serializes poorly:

- **Architecture** — components and their dependency/ownership relations (flowchart, 4+ related parts).
- **Data flow** — a value crossing 3+ hands, where "what talks to what, in what order" is the lesson (flowchart LR / sequence).
- **State machines** — states with non-linear transitions (stateDiagram-v2).
- **Call sequences** — multi-party request/response choreography, especially async or retried (sequenceDiagram).

## When to skip it

- A linear A→B→C that one prose sentence carries. A two-box diagram is noise.
- Restating a single function's internal steps — narrate them instead.
- Decoration: never add a diagram because the lesson "looks dry".
- Anything whose honest rendering needs features from the avoid-list below — prose beats a broken diagram.

One diagram per lesson is the norm; two is the ceiling. Every element in a diagram must be something the lesson verified (Axiom 3 applies to boxes and arrows too).

## Obsidian-safe syntax constraints

**Allowed diagram types** (conservative core, stable across Obsidian's bundled Mermaid versions): `flowchart`/`graph`, `sequenceDiagram`, `stateDiagram-v2`, `classDiagram`, `erDiagram`, `pie`, `gantt`.

**Hard rules:**

1. **No `%%{init}%%` directives, no `style`/`classDef`/`linkStyle` theming.** Obsidian themes diagrams for light/dark mode; hand-styling breaks one or the other.
2. **Quote any label containing punctuation:** `A["charge(token)"]` — parentheses, brackets, colons, commas or slashes in bare labels are parse errors in several Mermaid versions.
3. **No HTML in labels** (`<br/>`, `<b>`): keep labels short instead.
4. **Node IDs are plain ASCII identifiers** (`gatewayClient`, not `gateway-client!`), and never the bare word `end` (reserved in flowchart/sequence blocks) — use `finish`/`done`.
5. **No interaction or asset features:** `click`, callbacks, tooltips, and Font Awesome icons (`fa:fa-*`) don't work in Obsidian's sandbox.
6. **`stateDiagram-v2`, never v1;** `flowchart` preferred over legacy `graph`.
7. **No newer diagram types** (`mindmap`, `timeline`, `quadrantChart`, `sankey`, `xychart`, `block-beta`) — they require Mermaid versions Obsidian may not bundle.
8. **One statement per line; no trailing semicolons;** comments only as full `%% comment` lines.
9. **Keep it narrow:** ≤ ~8 nodes per flowchart row (prefer `TD` for deep, `LR` for wide-shallow); Obsidian panes clip very wide diagrams.
10. **sequenceDiagram:** declare `participant X as Readable Name` up front; `alt`/`else`/`loop`/`Note` blocks are fine; skip `autonumber` unless the prose refers to step numbers.

Before emitting a diagram, re-read it against rules 1–10 line by line; a lesson with a non-rendering diagram is worse than a lesson without one.
