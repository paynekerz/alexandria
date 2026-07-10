# Manual test — Task 2.2 (same function at all three depths)

Target: `execute()` in `Controller/Webhook/Index.php` (Basys_IQProPayment — the same real file as the task 2.1 test; all claims trace to code read that session). Each explanation below follows `references/depth.md` exactly. Save-offer blocks omitted here for readability; in a live session each response ends with one.

---

## intro

**What `execute()` does** — this method runs every time the payment gateway sends your store a message about a payment (a refund went through, a payment settled). Think of it as a mail clerk with one job: log every letter, and always sign the receipt.

It takes the message exactly as it arrived, pulls out the labeled pieces a human would care about — which transaction, which invoice, what happened, when — and files one row into a log table in the store's database, original message included. Then it replies "got it."

The surprising part: it replies "got it" **even when the filing fails**. That's deliberate. If the gateway doesn't get a receipt, it assumes the message got lost and sends it again, and again — the code's comments call this a "retry storm." So the clerk never refuses a letter; problems are written to an error log for a human, and the receipt goes out regardless. Nothing about your actual orders changes here — a separate scheduled task reads the log table later and does the careful work. Receiving is fast and dumb on purpose; processing is slow and careful, elsewhere.

## practitioner

**`execute()` is a receive-only webhook sink.** It reads the raw POST body, `json_decode`s it (silently coercing non-array results to `[]`), and maps selected fields — `traceId`, `resourceType`/`subType`, `resource.transactionId`/`invoiceId`/`status`, `actionDateTime` — through a `str()` normalizer (trim, empty→null, truncate to 64 chars) into an `EventLogger::log()` call. That's a single INSERT into `basys_iqpro_webhook_event`, raw payload stored alongside the extracted columns. The whole body of work sits in a `try/catch (\Throwable)`: any failure is logged and swallowed, and the method returns `{"received": true}` with HTTP 200 unconditionally.

Design intent, per the docblock: "Phase 1, receive and log only." Always-200 exists to stop the gateway's redelivery/backoff cycle; order mutation is deferred to the `ProcessWebhookEvents` cron, which consumes unprocessed rows from the same table. Two things to know before modifying: the class implements `CsrfAwareActionInterface` and unconditionally passes CSRF validation (machine caller — no form key), and there is **no signature verification yet**, also flagged in the docblock — the endpoint currently trusts any caller that can reach the URL.

## deep-dive

**Contract and boundaries.** `Index` implements `HttpPostActionInterface` (POST-only routing, by the interface's documented contract — not verified against framework source this session) and `CsrfAwareActionInterface`, where `createCsrfValidationException()` → `null` and `validateForCsrf()` → `true` (lines 71–79): an unconditional CSRF bypass, the standard shape for machine-to-machine endpoints. Combined with the docblock's "no signature verification yet," the trust boundary is currently *network reachability* — anyone who can POST to `/basys_iqpropayment/webhook/index` can insert rows. Forged rows reach the DB but their blast radius is bounded by what the cron consumer will later refuse to match; the row itself is cheap attacker-controlled storage (DoS-by-volume is the realer concern).

**Input handling edge cases** (lines 35–51): `json_decode($raw, true)` failure → `null` → coerced to `[]`, so a garbage body still logs a row with null columns and the raw body preserved — forensics survive malformed input. `$payload['resource']` non-array → `[]` guard. `str()` (81–88) collapses `null`/arrays to null, trims, maps `''`→null, truncates to 64 — so oversized upstream IDs are silently clipped; if iQ Pro+ ever ships >64-char trace IDs, correlation breaks quietly. `payload` stores `$raw` untruncated, so recovery is possible.

**Failure semantics** (60–66): `catch (\Throwable)` — not `Exception` — so even engine errors in the logging path can't propagate; the 200 receipt is effectively unconditional. Consequence: a *persistent* insert failure (table missing, DB down at insert but alive for the response) acknowledges deliveries while losing them — the gateway won't redeliver something we 200'd. The design accepts silent-loss-with-error-log over retry-storm; if that trade ever reverses, this catch block is the line to change. Note `lastInsertId()` cast to `int` in `EventLogger` (line 26) is the only success signal, and it's used solely for the info log's `id` — the response body carries no event identifier back to the gateway.

---

**Depth is recorded in frontmatter:** each of the three, if saved, produces `depth: intro|practitioner|deep-dive` in the session note (vault schema §3).
