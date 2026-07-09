---
project: Aurora
schemaVersion: 1
---

# Glossary — Aurora

## HMAC Verification

A way to prove a message really came from who it claims. Sender and receiver share a secret; the sender computes a signature from the message plus the secret, and the receiver recomputes it and compares. If they match, the message is authentic and untampered. Aurora uses it to reject forged webhooks.

Sessions: [[2026-06-19 webhook-handling]]

## Idempotency

An operation is idempotent when doing it once and doing it several times produce the same result. In payments this is a safety property: retried or redelivered requests must never charge or refund twice. Aurora gets it by sending unique keys with charges and by remembering which webhook events it has already processed.

Sessions: [[2026-06-12 checkout-tokenization-flow]], [[2026-06-19 webhook-handling]]

## PCI Scope

The parts of a system that store, process, or transmit real card numbers — and therefore fall under the PCI DSS security rules. The smaller the scope, the less there is to audit and secure. Aurora keeps its scope minimal by never letting card numbers reach the server.

Sessions: [[2026-06-12 checkout-tokenization-flow]]

## Tokenization

Swapping a sensitive value (like a card number) for a meaningless stand-in token issued by the party that holds the real value. The token is useless to a thief and safe to store; only the issuing gateway can map it back. Aurora's checkout tokenizes in the browser so the card number never touches the server.

Sessions: [[2026-06-12 checkout-tokenization-flow]]

## Webhooks

HTTP callbacks a service sends to your application when something happens on its side — the reverse of your app calling an API. Aurora listens for gateway webhooks to learn about refunds and chargebacks that happen after checkout.

Sessions: [[2026-06-19 webhook-handling]]
