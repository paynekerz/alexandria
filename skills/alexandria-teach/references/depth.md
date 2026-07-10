# Depth levels — precise semantics

Depth is chosen per session: the user's explicit request wins; otherwise config `defaultDepth`. State the level at the top of the lesson and record it in the session's `depth` frontmatter.

Depth changes **vocabulary, assumed background, and whether fundamentals are re-derived**. It never changes: the accuracy rules, the save offer, concept granularity (Decision 6), or glossary definitions (always written at intro level, per the vault schema).

## `intro` — assume zero prior knowledge

- **Reader:** someone who has never programmed in this stack — possibly never programmed at all.
- **Vocabulary:** plain language. Every term of art is either explained in the sentence where it first appears, or wiki-linked if already taught. "HTTP", "JSON", "endpoint", "controller" all count as terms of art.
- **Assumed background:** none. Explain what the framework is doing on the code's behalf ("Magento maps this web address to this class and runs `execute()`").
- **Fundamentals:** re-derived from first principles, briefly, at the moment they're needed. Analogies encouraged when they map cleanly.
- **Code excerpts:** small and narrated line-by-meaning, not line-by-line. Never paste a block and assume it speaks for itself.
- **Test:** a non-technical stakeholder could retell what the code does and why it's shaped that way.

## `practitioner` — assume a working developer

- **Reader:** a developer comfortable in the language and general web development, but not necessarily this framework or this codebase.
- **Vocabulary:** standard industry terms used without explanation (HTTP verbs, JSON, DI, CSRF, cron, idempotency-as-a-word). Framework-specific mechanics still get one clause of explanation on first appearance.
- **Assumed background:** general programming fundamentals. Not assumed: this framework's conventions, this codebase's architecture, this domain's rules (payments, etc. — explain briefly).
- **Fundamentals:** named, not re-derived ("the handler is CSRF-exempt — machine caller, no session"). Wiki-linked when previously taught.
- **Focus shifts to:** design decisions, data flow, how this piece connects to its neighbors, what you'd need to know to modify it safely.
- **Test:** a mid-level dev new to the repo could confidently make a first change to this area.

## `deep-dive` — assume a practitioner who wants internals

- **Reader:** someone with practitioner background in this stack who wants edge cases, failure modes, and rationale.
- **Vocabulary:** full technical vocabulary, framework terms included, no glossing.
- **Assumed background:** everything practitioner assumes, plus this framework's common conventions.
- **Fundamentals:** never re-derived. Prior concepts are wiki-linked references only.
- **Focus shifts to:** exact behavior at boundaries (what happens on malformed input, on partial failure, on concurrent delivery), security and performance trade-offs, alternatives the design rejected and why, precise line-level references.
- **Accuracy note:** depth is not license to speculate. Framework-internal claims still need verification — read the framework source, fetch its docs, or mark the claim explicitly ("by the interface's documented contract; not verified against framework source this session").
- **Test:** the code's author would nod along and learn at least one sharp observation.

## Choosing when the user is vague

Natural phrasings map as: "explain like I'm new / I'm not technical / from scratch" → `intro`; "I know PHP, just not Magento / quick orientation" → `practitioner`; "walk me through the internals / edge cases / why is it built this way" → `deep-dive`. If the user names a level, use it verbatim. Never silently change level mid-session; if the user asks to go deeper, say the level is changing — the session note records the final level.
