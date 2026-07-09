---
project: Atlas
schemaVersion: 1
---

# Glossary — Atlas

## Dependency Injection

Instead of a component building the tools it needs, the tools are handed to it from outside when it's created. This makes components swappable and testable — a test can hand in a fake tool where production hands in a real one. Atlas's pipeline injects each middleware's dependencies at wiring time.

Sessions: [[2026-07-01 request-pipeline]]

## Exponential Backoff

A retry strategy where the wait between attempts doubles each time — 1s, 2s, 4s, 8s — so a struggling service gets breathing room instead of a stampede of retries. Atlas's job retrier uses it for every failed job.

Sessions: [[2026-06-25 retry-idempotency]]

## Idempotency

An operation is idempotent when doing it once and doing it several times produce the same result. Atlas relies on it for safe job retries: handlers check a stable job ID before acting, so a job whose reply got lost can be retried without doing the work twice.

Sessions: [[2026-06-25 retry-idempotency]]

## Middleware

Small functions arranged in a fixed order that every request passes through before reaching its handler — each can inspect, modify, or reject the request. Atlas uses middleware for logging, authentication, and rate limiting.

Sessions: [[2026-07-01 request-pipeline]]
