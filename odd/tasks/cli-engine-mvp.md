# CLI Engine MVP

Objective: build the download engine and a working CLI for the heroes domain, with verified pagination, atomic manifest and resumable sync. GUI is deferred to the final phase.
Branch: `feat/cli-engine-mvp` · Delivery: single PR · Runner: `uv run pytest -q`

## Specs

S1. CLI-first. Implementation starts with a command-line interface; the GUI moves to the last phase of the plan.
Context: L5 — "modifica el plan para que la GUI este al final y en su lunar empezar con el CLI".

S2. Pagination correctness. Page size 500 (verified server maximum), `index` is a 1-based page number, `index=0` returns an empty page with HTTP 200. Every paged fetch MUST verify `len(records) == total` and fail loudly when it does not match. Silent partial data is the worst possible outcome for this product.

S3. Endpoint descriptor validated against three real shapes before generating the 94. The three cases: paged-with-envelope (`GET /api/heroes`), fixed single resource (`GET /api/academy/meta/version`, which is paged with `total == 1`), and path-parameterized per-entity (`GET /api/heroes/{hero_identifier}/stats`). The generator must agree with the hand-written descriptors, not the other way around.

S4. Defaults: `Accept-Encoding: gzip`, images disabled, concurrency 1, throttle 0.35s, quick sync as the default mode.

S5. First deliverable: download all 133 heroes with verified pagination, write the manifest, kill the process mid-run, resume without corrupting files or losing items.

S6. SHA-256 is the only change-detection signal. The API sends no ETag and no Last-Modified, only `cache-control: max-age=300`.

S7. Atomic writes. Manifest and download targets are written to a temp file and renamed; partial downloads use a `.part` suffix.

S8. Windows path sanitization. Reserved device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9), illegal characters, trailing dots/spaces, and length limits must be handled.

S9. No secrets or tokens in logs. `/api/user` endpoints require a JWT obtained through an in-game verification flow and stay out of scope for this milestone.

## Tasks

| ID | Task | Specs | Route | Status | Commit |
| -- | ---- | ----- | ----- | ------ | ------ |
| T1 | Project scaffold, `pyproject.toml`, settings and app paths | S1, S4 | inline | done | b35807a |
| T2 | HTTP client: gzip, throttle, bounded retry/backoff, error envelope parsing | S4, S9 | inline | done | b35807a |
| T3 | Verified paginator with completeness assertion | S2 | inline | done | b35807a |
| T4 | Atomic JSON manifest with item identity and hashes | S6, S7 | inline | done | 7e85cd2 |
| T5 | Safe output paths and slug sanitization | S8 | inline | done | 7e85cd2 |
| T6 | Endpoint descriptor for the three real shapes | S3 | inline | done | this commit |
| T7 | Heroes downloader: list, detail, stats, wallpapers with resume | S5 | inline | done | this commit |
| T8 | CLI commands: `heroes sync`, `heroes check`, `status` | S1 | inline | done | this commit |
| T9 | Live verification: pagination completeness, kill and resume | S2, S5 | inline | done | this commit |

## Log

L1. (user, verbatim) "Lee el archivo AGENTS.md y Formula un plan de implementación también crea el proyecto en la memoria local engram para guardar el contexto del proyecto"

L2. (user, verbatim) "MLBB Downloader no tiene nada que ver con mlbb-data incluso no usan la misma API por eso pedí crear un nuevo Proyecto en la memoria local Engram"

L3. (user, verbatim) "Entre de empezar revisa que hace la API a qué tienes acceso y con que trabajaremos en base a eso veremos si tenemos que modificar el plan"

L4. (user, verbatim) "Que me recomiendas?"

L5. (user, verbatim) "Si implemente lo que me recomendaste y modifica el plan para que la GUI este al final y en su lunar empezar con el CLI"

L6. API verification (2026-11-26) produced the runtime facts this document depends on: default page size 12, max 500, `index` 1-based with `index=0` empty, no ETag/Last-Modified, zstd by default with gzip available, heterogeneous raw payloads, esports non-uniform across leagues, images served through the wsrv.nl CDN, auth requires an in-game verification code. Full detail stored in Engram under `api/runtime-behavior`.

L7. Decision: GUI moved after packaging-preparation phase. Rationale: all implementation risk sits in the engine (pagination correctness, resume, ~2200-call volume); Qt adds no information until the engine is trustworthy, and debugging QThread signals while the engine is still moving doubles uncertainty.

L8. Decision: no per-endpoint pydantic models. The same entity returns different shapes from list and detail endpoints, so payload modeling is a maintenance liability with no payoff. Pydantic is used only for manifest and settings. Upstream schema hashes will drive drift detection later.

L9. Correction to S3 after implementation: `/api/academy/meta/version` is not unpaged. It uses the same envelope and returns `total == 1`. The descriptor therefore models three axes (paged shape, fixed resource, path-parameterized enumeration) rather than three envelopes.

L10. Verification (T1-T5): 30 tests pass, `ruff check` and `ruff format --check` clean. Paginator covers multi-page assembly, `index` starting at 1, the 500 cap, empty collections, missing totals, and raises `IncompletePageError` when the server under-delivers.

L11. Live verification (T7-T9, 2026-11-26):
- `heroes sync --limit 2` -> 17 artifacts (1 index + 2 x 8 sub-resources) in 11.2s.
- Second run -> `downloaded=0 skipped=17` in 1.2s.
- Kill test: process killed after 20s with `items=25` flushed. Resume -> `downloaded=72 skipped=25`. Final dataset identical byte for byte to the clean run (870442 bytes), proving idempotency.
- Integrity script: 97 artifacts, `len(records) == total` for all, zero mismatches, zero empty.
- `check` on a complete set -> `unchanged=17`. After deleting one file -> `missing=1` and the exact key is printed.

L12. Design correction found during verification: `check_heroes` originally walked the entire remote catalogue (133 heroes x 8 = 1064 calls) even when only 2 heroes were stored, and it ignored any limit. It now derives the hero ids from the manifest and only re-fetches what exists locally, reporting the rest as a `not_downloaded` count. Measured: 17 local artifacts checked in 10.0s with `not_downloaded=131` instead of a 10-minute crawl.
