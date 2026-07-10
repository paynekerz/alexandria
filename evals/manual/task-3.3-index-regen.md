# Manual test — Task 3.3 (project index, lossless regeneration)

`_index.md` is rendered by `render_index()` in `scripts/vault.py` purely from session-note frontmatter (`date`, filename, `depth`, `concepts`, `files`, `commit`), newest first, ties broken by filename — nothing in it is authored, so deleting it loses nothing.

## DOD proof — delete and rebuild, byte-identical

For each project in `docs/example-vault/`: SHA-256 the index, `rm` it, run `python vault.py regen-index <Project>`, SHA-256 again.

```text
Aurora:     deleted=yes  before=87a91832...c448e77b4c
Aurora:                   after=87a91832...c448e77b4c  -> IDENTICAL
Atlas:      deleted=yes  before=3703ace4...05ac1c40dd
Atlas:                    after=3703ace4...05ac1c40dd  -> IDENTICAL
Alexandria: deleted=yes  before=442fd6d4...0dc1cbcdb
Alexandria:               after=442fd6d4...0dc1cbcdb  -> IDENTICAL
```

`git status docs/example-vault` after the run: clean — the rebuilt files are exactly the committed ones.

Aurora and Atlas indexes were hand-written in Phase 0.3, before this code existed; regeneration reproducing them byte-for-byte is also pinned as a unit test (`test_index_regen_byte_identical`), so any future format drift fails CI-style at test time rather than corrupting vaults.
