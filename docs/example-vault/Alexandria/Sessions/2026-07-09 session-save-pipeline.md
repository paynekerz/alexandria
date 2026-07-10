---
project: Alexandria
title: What happens when a lesson is saved
date: 2026-07-09
depth: intro
concepts:
  - Atomic Write
  - Derived Data
files:
  - scripts/vault.py
commit: 2979b1b
sources: []
schemaVersion: 1
---

# What happens when a lesson is saved

## Lesson

When you tell the librarian to save a lesson, one script call does everything: `save_session()` in `scripts/vault.py`. It runs four steps, always in the same order.

First it writes the session note itself — frontmatter plus lesson — using the same [[Alexandria/_glossary#Atomic Write|atomic write]] every vault file gets, so an interrupted save can't leave a torn note behind. Second, it merges the session's concepts into the project glossary: a brand-new concept gets its definition added, while a concept the glossary already knows just gains a link to the new session — the existing definition is deliberately never rewritten. Third, it rebuilds the project's `_index.md` table from scratch by reading every session's frontmatter. Fourth, it checks whether any concept from this session is now taught in two or more projects, and if so writes the shared concept page under `_Concepts/`.

Steps three and four never append to the old files — they regenerate them completely. That works because the index and concept pages are [[Alexandria/_glossary#Derived Data|derived data]]: nothing in them is hand-written, so recomputing them from the session notes always produces the truth, and drift between notes and indexes can be repaired by just regenerating.

## Files

- `scripts/vault.py` @ `2979b1b`
