# A day with Alexandria

This is one realistic day of use, start to finish, against a small sample repo: `sample-shop`, a PHP webhook handler with two files -- `src/webhook.php` receives payment-gateway callbacks, and `src/verify.php` checks their signatures. Every command, exit code, and output shape below was run against the current scripts before this doc was written; nothing here is aspirational.

You'll need Alexandria installed per the [README](../README.md). That's it -- the first invocation handles the rest.

## 9:00 -- First invocation, one-time setup

You open Claude Code in `sample-shop` and ask:

```text
> alexandria, teach me src/verify.php
```

There's no config yet, so before any teaching happens, the skill runs its one-time interview: vault location (default `~/Desktop/Alexandria`), teaching model, default depth, quiz on or off. You take the defaults. Behind the answers, `scripts/setup.py` does the deterministic work:

```text
Config written: ~/.alexandria/config.json
Vault root:     ~/Desktop/Alexandria
Teacher agent:  ~/.claude/agents/alexandria-teacher.md (model: sonnet)
  created _Concepts
  created .alexandria\meta.json
  created Welcome.md
```

Setup is a detour, never the destination: the lesson you asked for starts in the same turn.

## 9:02 -- The first lesson

Teach checks the library first (`recall.py search "sample-shop" --query "webhook signature verification"`). The answer comes back `"projectExists": false` -- no library for this project yet, so everything gets taught fresh.

The lesson itself runs at `intro` depth, on the model you picked, and only says things traceable to the code it read: what `verify()` does, why the HMAC is recomputed over the raw body, why the comparison uses `hash_equals()`. No external links appear -- a plain code walkthrough doesn't earn a fetch.

Every teach response ends the same way:

```text
---
**Save this lesson?** Say "save" and alexandria-librarian will file it in your library (concepts confirmed with you first).
**Draft concepts this session:** HMAC Signature Verification, Constant-Time Comparison
```

## 9:10 -- Save

You say "save". The librarian shows you the two draft concepts and asks which to keep -- you curate the list; nothing enters your library unconfirmed. Then it assembles the payload (project, title, depth, files read, the commit hash `git rev-parse --short HEAD` reports, your confirmed concepts with intro-level definitions) and pipes it through the one gate all vault writes go through:

```text
$ python vault.py save-session < payload.json
note:     ~/Desktop/Alexandria/sample-shop/Sessions/2026-07-18 webhook-signature-verification.md
glossary: added HMAC Signature Verification, Constant-Time Comparison
index:    ~/Desktop/Alexandria/sample-shop/_index.md
concepts: none - no saved concept spans 2+ projects
```

One note, two new glossary entries, an index row. Open the vault in Obsidian and the lesson is there, wiki-linked to its glossary entries.

## 13:00 -- Recall instead of re-teaching

After lunch you've forgotten the details and ask:

```text
> alexandria, have we covered webhook signatures before?
```

Recall runs the same search -- now it hits:

```json
{
  "projectExists": true,
  "taughtConcepts": ["Constant-Time Comparison", "HMAC Signature Verification"],
  "sessions": [{
    "note": "2026-07-18 webhook-signature-verification",
    "matched": ["concept: HMAC Signature Verification", "title"],
    "files": ["src/verify.php"],
    "commit": "e78b34f"
  }]
}
```

So the answer is a link, not a re-explanation: "You covered this in [[2026-07-18 webhook-signature-verification]] (2026-07-18, intro depth)" -- plus an offer to teach whatever your new question asked that the saved lesson didn't cover. Your library is scoped per project: nothing from any other project's folder was read to answer this.

## 15:30 -- The code changes

You commit a change to `src/verify.php` (a 5-minute clock-skew tolerance on the timestamp header). The saved lesson now describes code that no longer matches the repo.

## 16:00 -- Drift catches it

Next time recall surfaces that session, it runs the drift check: stored commit + file list against current git state.

```json
{
  "note": "2026-07-18 webhook-signature-verification",
  "commit": "e78b34f",
  "status": "stale",
  "changedFiles": ["src/verify.php"]
}
```

You get flagged, not silently misled: "this explanation predates changes to `src/verify.php` -- want a refreshed lesson?"

You say yes. Teach re-teaches at the same depth, covering what changed; at save time the new note carries `supersedes: "2026-07-18 webhook-signature-verification"` and links its predecessor in the prose. The old note is never edited or deleted -- run drift again and it reports:

```json
{"note": "2026-07-18 webhook-signature-verification-refresh", "status": "fresh"}
{"note": "2026-07-18 webhook-signature-verification", "status": "superseded",
 "supersededBy": "2026-07-18 webhook-signature-verification-refresh"}
```

Your learning history stays intact; the current lesson is the fresh one.

## 16:05 -- End of day

Two notes, a glossary, an index, all machine-checkable:

```text
$ python vault_lint.py
clean: 0 findings
```

That's the whole loop: teach reads and explains, you curate what's saved, the librarian files it deterministically, recall links instead of re-teaching, and drift tells you when the code has moved on. Tomorrow, the library is bigger and the lessons are still true -- or flagged when they aren't.

## Demo recording

The README's terminal recording follows this exact narrative; the shot-by-shot capture script is in [DEMO-SCRIPT.md](DEMO-SCRIPT.md).
