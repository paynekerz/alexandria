# Comprehension check — format and grading

## Writing the questions

- 2 questions for a 1–2 concept session, 3 for a session with 3+ confirmed concepts.
- Each question maps 1:1 to a confirmed concept from **this session's** draft list; every question names an idea the lesson actually taught (a wiki-linked already-taught concept may appear only as supporting context, not as the thing tested).
- Test understanding, not recall of phrasing: "why does the controller always return 200?" beats "what does line 68 return?".
- Depth-appropriate: intro sessions get intro-level questions.

## Grading

- Grade against what the lesson established — not against knowledge the lesson didn't cover.
- Generous on wording, strict on mechanism: a correct idea in the user's own words is Correct.
- An incorrect answer gets exactly one corrective line, anchored to the lesson.
- Partial answers: mark Correct or Incorrect, never fractional. When torn, credit the user.

## Result format

Frontmatter (vault schema §3): `quizScore: "<correct>/<asked>"`, e.g. `"2/3"`.

Note section (last section of the note, after Sources if present):

```markdown
## Comprehension

| # | Question | Result |
|---|---|---|
| 1 | Why does the endpoint reply "received" even on failure? | Correct |
| 2 | Where does the order actually get updated? | Incorrect — the cron job applies events; the controller only logs them. |

Score: 1/2
```

The table row for an incorrect answer carries the one-line correction after the em-dash. `Score:` always matches `quizScore` exactly (vault lint will compare them).

## When the quiz is skipped

Nothing is written: no `quizScore` frontmatter, no `## Comprehension` section, no "quiz skipped" note. Absence is the record.
