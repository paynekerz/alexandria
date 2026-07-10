---
project: Alexandria
title: How vault writes stay inside the vault
date: 2026-07-09
depth: intro
concepts:
  - Path Traversal
  - Atomic Write
files:
  - scripts/vault.py
commit: ceb9a01
sources: []
schemaVersion: 1
---

# How vault writes stay inside the vault

## Lesson

Every file Alexandria saves passes through one narrow door: `scripts/vault.py`. Before any write, its `resolve()` method joins the requested relative path onto the vault root, then fully resolves the result — collapsing `..` segments and following symlinks — and checks that it still sits under the root. A path like `../evil.md` that tries to climb out of the vault is a [[Alexandria/_glossary#Path Traversal|path traversal]] attempt, and `resolve()` raises a refusal before anything touches disk. Absolute paths and drive-letter paths are refused outright, and every public method funnels through this one checkpoint.

The write itself is just as careful. `write_note()` never edits the real file in place: it writes the full content to a temporary file in the same folder, then swaps it over the target with `os.replace()`, which the operating system performs as a single step. That two-step dance is an [[Alexandria/_glossary#Atomic Write|atomic write]] — if the program crashes mid-save, the vault still holds the old, intact note rather than a half-written one.

## Files

- `scripts/vault.py` @ `ceb9a01`
