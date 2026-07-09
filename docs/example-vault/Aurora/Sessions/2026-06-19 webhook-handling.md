---
project: Aurora
title: What happens when a webhook arrives
date: 2026-06-19
depth: intro
concepts:
  - Webhooks
  - HMAC Verification
  - Idempotency
files:
  - src/Webhook/Listener.php
commit: e4f5a6b
sources: []
schemaVersion: 1
---

# What happens when a webhook arrives

## Lesson

Some payment events happen after checkout is over — a refund settles, a chargeback lands. The gateway tells Aurora about them by calling back over HTTP. These callback messages are [[Aurora/_glossary#Webhooks|webhooks]], and `src/Webhook/Listener.php` is the door they knock on.

Anyone on the internet could POST to that door, so the listener's first job is proving the message really came from the gateway. Each webhook carries a signature computed from the message body and a secret only Aurora and the gateway share; the listener recomputes it and compares. That check is [[Aurora/_glossary#HMAC Verification|HMAC verification]] — mismatch means the message is dropped unprocessed.

Gateways also redeliver webhooks when they aren't sure the first delivery landed. The listener records each event ID and skips ones it has already processed, so a redelivered "refund settled" event doesn't refund twice. We met this retry-safe property in [[2026-06-12 checkout-tokenization-flow]] — it's [[Aurora/_glossary#Idempotency|idempotency]] again, this time on the receiving side.

## Files

- `src/Webhook/Listener.php` @ `e4f5a6b`
