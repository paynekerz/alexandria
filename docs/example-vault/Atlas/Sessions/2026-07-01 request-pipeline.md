---
project: Atlas
title: How a request travels through the pipeline
date: 2026-07-01
depth: intro
concepts:
  - Middleware
  - Dependency Injection
files:
  - src/server/pipeline.ts
commit: 3f2e1d0
sources: []
schemaVersion: 1
---

# How a request travels through the pipeline

## Lesson

Every request that reaches Atlas passes through the same corridor of checkpoints before any real work happens: logging, then authentication, then rate limiting, then the route handler. Each checkpoint is a small function that can inspect the request, act on it, and pass it along — or stop it cold. These functions are [[Atlas/_glossary#Middleware|middleware]], and `src/server/pipeline.ts` is where the corridor is assembled, in order.

The interesting part is how each middleware gets its tools. The auth middleware needs a token verifier; the rate limiter needs a counter store. They don't build these themselves — the pipeline hands each middleware what it needs when wiring it up. That hand-me-your-tools pattern is [[Atlas/_glossary#Dependency Injection|dependency injection]], and it's why tests can slip a fake counter store to the rate limiter without touching real infrastructure.

## Files

- `src/server/pipeline.ts` @ `3f2e1d0`
