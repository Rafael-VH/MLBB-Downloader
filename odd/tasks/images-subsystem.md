# Images subsystem

Branch: `feat/academy-addon` Â· Delivery: work-unit commits Â· Runner: `uv run pytest -q`

## Specs

- **S1** Images are binary artifacts: downloaded bytes, sha256 hashed, stored atomically, tracked in manifest.
- **S2** Manifest v2 is backward-compatible with v1 (read v1, write v2). New fields: `kind`, `source_url`, `content_type`.
- **S3** Image identity dedupes by canonical source URL; `wsrv.nl/?url=` wrappers are unwrapped for identity.
- **S4** Domain image extraction is pure (no IO). HTTP bytes and filesystem writes live in adapters.
- **S5** Sync is resumable and idempotent; check reports missing/changed without downloading.
- **S6** No GUI, no esports. Existing 60 tests keep passing.

## Tasks

| ID | Spec | Route | Status | Commit |
| -- | ---- | ----- | ------ | ------ |
| T1 | S1 S2 S3 | inline | done | this commit |
| T2 | S1 S4 | inline | done | `d343f4f` |
| T3 | S3 S4 | inline | 6f40f89 | â€” |
| T4 | S1 S5 | inline | pending | â€” |
| T5 | S6 | inline | done | 2a90b8 |
2a90b8 |
2a90b8 |

## Log

- **L1** (user): approved plan ("Si") with 3 decisions: canonical origin URL identity, heroes+academy catalog scope, manifest v1->v2 compatible.
- **L2** T1 adds manifest v2 optional fields, canonical image URL/key, and `DataStore.save_bytes`.
