---
project: Atlas
title: How retry logic avoids doing work twice
date: 2026-06-25
depth: intro
concepts:
  - Idempotency
  - Exponential Backoff
files:
  - src/jobs/retry.ts
  - src/jobs/queue.ts
commit: 9c8d7e6
sources:
  - https://developer.mozilla.org/en-US/docs/Glossary/Idempotent
schemaVersion: 1
---

# How retry logic avoids doing work twice

## Lesson

Atlas talks to services that sometimes don't answer. When a job fails, `src/jobs/retry.ts` tries it again — but blind retries create two problems, and this file solves both.

Problem one: what if the job actually succeeded and only the *reply* got lost? Retrying would do the work twice — send two emails, create two invoices. Atlas prevents this by giving every job a stable ID and having handlers check "have I already done this ID?" before acting. A job that's safe to repeat like this is [[Atlas/_glossary#Idempotency|idempotent]], and `retry.ts` refuses to retry any job type not marked as such.

Problem two: when a service is down, a thousand jobs retrying every second is a stampede that keeps it down. So `retry.ts` waits 1 second before the first retry, 2 before the next, then 4, 8, 16 — doubling each time. That widening-gap pattern is [[Atlas/_glossary#Exponential Backoff|exponential backoff]], and it gives the struggling service room to recover.

`src/jobs/queue.ts` stores the attempt count each job carries, which is how `retry.ts` knows how long the next wait should be.

## Files

- `src/jobs/retry.ts` @ `9c8d7e6`
- `src/jobs/queue.ts` @ `9c8d7e6`

## Sources

- [Idempotent — MDN Glossary](https://developer.mozilla.org/en-US/docs/Glossary/Idempotent)
