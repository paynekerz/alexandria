---
project: Alexandria
schemaVersion: 1
---

# Glossary — Alexandria

## Atomic Write

Writing a file's new content to a temporary file first, then swapping it into place in one indivisible operating-system step. A crash mid-save leaves the old file intact instead of a half-written one. Alexandria writes every vault note this way.

Sessions: [[2026-07-09 session-save-pipeline]], [[2026-07-09 vault-write-safety]]

## Derived Data

Files whose entire content is computed from other files rather than authored by hand. Alexandria's `_index.md` and `_Concepts/` files are derived from session frontmatter, so they can be deleted and rebuilt identically at any time — hand edits to them are always safe to overwrite.

Sessions: [[2026-07-09 session-save-pipeline]]

## Path Traversal

A bug or attack where a crafted path (usually built from `..` segments, absolute paths, or symlinks) escapes the directory it was supposed to stay inside, letting code read or write files it never should. Alexandria's `resolve()` refuses any vault path that lands outside the vault root.

Sessions: [[2026-07-09 vault-write-safety]]
