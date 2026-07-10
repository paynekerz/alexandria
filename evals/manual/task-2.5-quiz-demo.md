# Manual test — Task 2.5 (comprehension check, enabled vs disabled)

Both simulations continue the task 2.1 session (project `IQProPayment`, intro depth, confirmed concepts: Webhooks *(already taught)*, Deferred Processing, CSRF Protection). Per `references/quiz.md`, questions target only this session's confirmed concepts; the already-taught concept (Webhooks) is not tested.

## Simulation A — `quizEnabled: true`

> **User:** great, save it.
>
> **Alexandria:** Before I file it — quick check, three questions (say "skip" to skip):
>
> 1. The controller replies "received: true" even when saving the event fails. Why is that deliberate?
>
> **User:** because otherwise the gateway keeps resending it over and over
>
> **Alexandria:** Correct — an error response triggers the gateway's redelivery cycle; acknowledging keeps it calm.
>
> 2. The webhook controller never touches an order. Where does the order actually get updated, and why there?
>
> **User:** the controller updates it right after inserting the row
>
> **Alexandria:** Incorrect — the scheduled cron job (`ProcessWebhookEvents`) reads unprocessed rows later and applies them; receiving stays fast so a slow order save can't stall the gateway.
>
> 3. This endpoint accepts POSTs without the token Magento normally requires. Why is skipping that check acceptable here?
>
> **User:** the caller is the gateway server, not a browser — there's no user session or form token to check
>
> **Alexandria:** Correct.
>
> Score: **2/3**. Handing the session to the librarian with the quiz result included.

**What lands in the saved note:**

Frontmatter gains:

```yaml
quizScore: "2/3"
```

Note body gains (final section):

```markdown
## Comprehension

| # | Question | Result |
|---|---|---|
| 1 | Why does the endpoint reply "received: true" even when logging fails? | Correct |
| 2 | Where does the order actually get updated, and why there? | Incorrect — the cron job applies events later; the controller only receives and logs. |
| 3 | Why is skipping Magento's CSRF token check acceptable on this endpoint? | Correct |

Score: 2/3
```

## Simulation B — `quizEnabled: false` (no per-session override)

> **User:** great, save it.
>
> **Alexandria:** Confirming the concept list with you and handing the session to the librarian.

No questions asked. The saved note has **no** `quizScore` frontmatter field and **no** `## Comprehension` section — absence is the record.

## Override checks (rules as written in SKILL.md Step 6)

| Config | User says | Result |
|---|---|---|
| `true` | "skip the quiz" | no quiz, nothing written |
| `false` | "quiz me" | quiz runs, results written |
