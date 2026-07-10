# External source rules

External material is **supplementary and conditional** — a lesson is complete without it. These rules decide when to look, where to look, and what may enter a note.

## Rule 0 — Most lessons need zero external sources

Fetch external material only when **both** hold:

1. The lesson teaches a *concept* (not just a walkthrough of what specific code does), **and**
2. That concept genuinely benefits from outside treatment — it's novel to the user, foundational enough to deserve a canonical reference, or served distinctly better by a visual/lecture format.

A simple code walkthrough fetches nothing. "The user might like a link" is not a reason; a link that doesn't earn its place is noise in the note forever. Default is **no fetch**.

## Rule 1 — Tier 1 first, always

Candidates come from config `tier1Sources` (see `docs/CONFIG.md` §2), filtered by scope:

- `general` entries — any concept. `official-docs` is a sentinel: resolve it to the official documentation site for the concept's language/framework/standard (php.net, docs.python.org, MDN for web platform topics, the framework's own docs site).
- `algorithms` entries (LeetCode) — **only** for algorithm and data-structure concepts. Link problems or explore cards that exercise the concept, **never** paywalled/premium solutions. One problem that exercises the concept beats a list of five.
- `video` entries (curated YouTube channels) — only when a visual or lecture treatment adds something prose can't (spatial/animated intuition, a full-course treatment).

Search order within Tier 1: official docs for the stack at hand first, then course platforms (MIT OCW, Harvard PLL, Stanford Online), then scope-specific entries. Stop at the first strong hit — one or two links per concept, maximum.

## Rule 2 — Tier 2 only on a Tier 1 miss

If no Tier 1 entry covers the concept, the open web may be searched. Requirements:

- The note (and the lesson) label the link as Tier 2 and record that Tier 1 was checked and missed — one line, e.g. `Tier 2 (no Tier 1 coverage): <link>`.
- Prefer primary/practitioner sources (vendor engineering docs, spec authors, well-maintained references) over content farms.
- The same verification rule applies as Tier 1 — no exceptions.

## Rule 3 — Every link is fetched and verified alive before inclusion

Before any URL enters a lesson or a note's `sources` frontmatter:

1. **Fetch it, this session.** A URL from memory is a guess; guessed URLs are how hallucinated links happen (Axiom 3).
2. **Confirm it's alive** — the fetch succeeds and returns real content, not a 404/error/placeholder page.
3. **Confirm it covers the concept** — skim the fetched content; a live page that doesn't actually teach the concept is excluded too.

A link that fails any check is dropped silently from the lesson (and, if it was the only candidate, the lesson simply ships without a source — see Rule 0). Never include an unfetched link, never "verify later".

## What enters the note

Verified links appear in the lesson's `## Sources` section as `[title](url)` and, identically, in the `sources[]` frontmatter array — nowhere else. Frontmatter and body must match 1:1 (vault lint checks this).
