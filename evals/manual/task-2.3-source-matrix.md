# Manual test — Task 2.3 (tiered source retrieval, four-case DOD matrix)

Run 2026-07-09 against `references/sources.md`. Every URL below was live-fetched during the test; nothing is from memory.

## Case (a) — common concept, strong Tier 1 coverage → Tier 1 link only

- **Concept:** CSRF Protection (from the task 2.1 lesson's draft concepts).
- **Tier 1 path:** `official-docs` sentinel → MDN (official web-platform docs).
- **Fetch:** `https://developer.mozilla.org/en-US/docs/Glossary/CSRF` → live; title "Cross-site request forgery (CSRF) - Glossary | MDN"; covers the concept (definition, vulnerability conditions, defenses).
- **Result:** ✅ lesson would include exactly this one Tier 1 link. No Tier 2 search performed (Tier 1 hit → stop).

## Case (b) — niche concept → documented Tier 2 fallback

- **Concept:** webhook retry storms / redelivery backoff (surfaced by the same lesson).
- **Tier 1 path:** no official language/framework doc owns this operational pattern; not course material on MIT OCW / Harvard PLL / Stanford Online; not an algorithm (LeetCode out of scope); no video benefit. **Tier 1 miss.**
- **Tier 2:** web search → candidate selected for being a primary practitioner source (webhook infrastructure vendor documentation, not a content farm). Fetch: `https://www.svix.com/resources/webhook-best-practices/retries/` → live; title "Webhook Retry Best Practices"; covers retry schedules, backoff, redelivery.
- **Result:** ✅ included with the required label, exactly as the note would carry it:
  `Tier 2 (no Tier 1 coverage): [Webhook Retry Best Practices — Svix](https://www.svix.com/resources/webhook-best-practices/retries/)`

## Case (c) — simple code walkthrough → zero external fetches

- **Evidence:** the task 2.1 intro lesson (`task-2.1-intro-lesson.md`) — a walkthrough of `Controller/Webhook/Index.php` — shipped with `sources: none fetched`, per Rule 0. No fetch was made while producing it.
- **Result:** ✅ zero fetches on a plain walkthrough.

## Case (d) — dead link injected → excluded from output

- **Injected candidate:** `https://developer.mozilla.org/en-US/docs/Glossary/RetryStormMitigation` (plausible-looking, fabricated).
- **Verification fetch:** HTTP **404 Not Found**.
- **Result:** ✅ link dropped; it appears in no lesson text and no `sources` frontmatter. (Had it been the only candidate, the lesson would ship sourceless per Rule 0/Rule 3.)

## Matrix summary

| Case | Expected | Observed | Pass |
|---|---|---|---|
| (a) common concept | Tier 1 link only | 1 MDN link, verified live, no Tier 2 search | ✅ |
| (b) niche concept | labeled Tier 2 fallback | Tier 1 miss documented, 1 verified Tier 2 link | ✅ |
| (c) simple walkthrough | zero fetches | zero fetches (task 2.1 artifact) | ✅ |
| (d) dead link | excluded | 404 detected, excluded | ✅ |
