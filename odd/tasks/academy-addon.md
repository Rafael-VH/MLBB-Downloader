# Academy + Addon

Objective: extend the engine to the academy domain (game data) and add the two addon tools as interactive commands, without duplicating resume/check logic per domain.
Branch: `feat/academy-addon` · Delivery: single PR · Runner: `uv run pytest -q`

## Specs

S1. One engine. Every domain describes what to download as an `Artifact` (endpoint, params, relative path); a single implementation owns resume, atomic writes, hashing, flush policy and reports. No domain carries its own copy of that logic.
Context: the heroes downloader proved the logic; keeping two copies would let them drift.

S2. Resume is manifest-driven and idempotent. A second run downloads 0. A crash loses at most one flush window (25 artifacts) of manifest entries; re-fetched files are atomic and hash-verified, so lost entries cost work, never correctness.

S3. Check is proportional to local data and writes nothing. It re-fetches manifest entries (plus the domain index to count entities never downloaded) and never crawls the remote catalogue.

S4. Academy game-data coverage: `meta/version`, `heroes/catalog`, `roles`, `equipment`, `equipment/expanded`, `spells`, `emblems`, `ranks`, `heroes` (unfiltered), plus per hero: `lane`, `stats`, `counters`, `teammates`, `trends`.

S5. Lanes are derived, not guessed. `builds` and `win-rate/timeline` require a `lane` query param; they are fetched only for the lanes the hero actually plays, read from the stored `lane` artifact (`road_sort_id` 1..5 → exp/mid/roam/jungle/gold). Never request all five blindly.

S6. User-generated content is excluded from bulk sync. `/academy/recommended` has `total: 10000` and `/academy/heroes/{id}/recommended` had 204 records for hero 1; the detail payload was measured byte-identical to the list record (1800 bytes, same keys), so per-record detail calls add nothing. `/academy/ranks/{rank_id}` is redundant with the rank list: 29 ranges cover 1..9999 and the detail record duplicates the list record. These are catalogued but not enumerated.

S7. Discontinued endpoints are not failures. `GET /academy/heroes/ratings` answers HTTP 200 with `code: 10407`, `message: "接口下线"`, `data: null`. That must surface as `unavailable` (non-fatal, reported once), never as a parse error and never as a red failure on every run. Normal envelopes use `code: 0`, so the signal is unambiguous.

S8. Addon is interactive only. `win-rate-calculator` (required `match-now`, `wr-now`, `wr-future`) and `ip` are one-shot commands, never part of a bulk download. The win-rate endpoint answers with `{status: "success", ...}` instead of the standard envelope.

S9. Verification: unit tests, lint clean, live sync with `--limit`, rerun idempotency, `check`, and a full academy run against the real API.

## Tasks

| ID | Task | Specs | Route | Status | Commit |
| -- | ---- | ----- | ----- | ------ | ------ |
| T1 | Envelope-level API failure detection (`code` != 0 with `data: null`) | S7 | inline | done | 9103b09 |
| T2 | Generic artifact engine: sync, check, manifest walk, flush policy | S1, S2, S3 | inline | done | c1f3257 |
| T3 | Port heroes onto the engine, preserving behavior and tests | S1 | inline | done | c1f3257 |
| T4 | Academy descriptors and downloader with derived lanes | S4, S5, S6 | inline | done | 813b9fa |
| T5 | Addon commands: `win-rate`, `ip` | S8 | inline | done | c8c7756 |
| T6 | Tests, live verification, README | S9 | inline | done | a444f97 |

## Log

L1. (user, verbatim, approving this milestone) "Si"

L2. (user, verbatim, earlier instruction this milestone derives from) "Si implemente lo que me recomendaste y modifica el plan para que la GUI este al final y en su lunar empezar con el CLI"

L3. API shapes verified live (2026-11-26) before writing code:
- Static collections, all paged with envelope: version 1, catalog 133, roles 7, equipment 184, equipment/expanded 152, spells 12, emblems 26, ranks 29, heroes filter 133.
- `lane` artifact per hero: one record, `data.hero.data.roadsort` lists the lanes the hero plays. Observed `road_sort_id` 1 (Exp Lane), 4 (Jungle), 5 (Gold Lane); builds accepted `exp|mid|roam|jungle|gold` and rejected `exp-lane`/`mid-lane` with HTTP 422.
- `builds` and `win-rate/timeline` return 1 record per lane. `trends` accepts `days` 7/15/30 (default 7); `stats` and `trends` accept `rank` all/epic/legend/mythic/honor/glory (default all). Only defaults are downloaded.
- `stats`, `counters`, `teammates`, `trends` return 1 record per hero. `matchups` does not exist (HTTP 404) — it was in the earlier endpoint list, and the real list from OpenAPI has `teammates` instead.
- `ranks/{rank_id}`: path value is a rank number 1..9999, not the record id. All of 1, 4, 5, 10, 25, 50, 100 and 9999 returned the covering range; the detail record is the list record.
- `/academy/recommended` total 10000; hero 1 recommended total 204; detail identical to list.
- `/academy/heroes/ratings` -> HTTP 200, `code: 10407`, `message: "接口下线"`, `data: null`. `/academy/heroes/ratings/{subject}` -> HTTP 422.
- Addon: `win-rate-calculator` -> `{status: "success", match_now, wr_now, wr_future, required_no_lose_matches, message}`; invalid target -> HTTP 400 with `{status: "error", code: "BAD_REQUEST", message}`. `/addon/ip` -> `{code: 0, msg: "ok", data: {city, state, country, lang}}` (note `msg`, not `message`).

L4. Decision: UGC and redundant endpoints stay catalogued but out of bulk sync (S6). Downloading 10000 community records plus ~200 per hero would multiply the dataset by an order of magnitude while duplicating payload already present in the list response.

L5. Decision: two-pass academy sync. Pass 1 stores collections and per-hero artifacts including `lane`; pass 2 reads the stored `lane` artifacts and schedules `builds`/`win-rate` only for the lanes found. This survives resume: skipped lanes are read from disk, not re-fetched.

L6. Decision: the check path becomes manifest-driven (`check_manifest`) instead of domain-planned. It is exactly proportional to what exists locally and removes duplicated planning code between heroes and academy.

L7. Volume estimate for a full academy run: 9 collection pages + 133 x 5 per-hero artifacts + roughly 2 lanes x 2 lane artifacts per hero ≈ 1200 requests ≈ 7-8 minutes at the default 0.35s throttle.

L8. Decision: `--limit` removed from `heroes check`. Check is manifest-driven now, so a limit no longer describes anything real; keeping a flag that does nothing is worse than removing it. `--limit` stays on both sync commands, where it selects heroes to download.

L9. Verification (T1-T5): 59 tests pass, `ruff check` and `ruff format --check` clean. New coverage: HTTP 200 error envelopes, engine resume/force/failure isolation/optional artifacts, manifest-driven check, academy task planning, lane derivation from sort ids and titles, derived lane scheduling, UGC and discontinued exclusion, addon parameters and validation errors, CLI error guard.

L10. Live verification, limited academy run (2026-11-26): `academy sync --limit 3` -> 30 artifacts in 24.3s (9 collections + 3 x 5 per-hero + 2 lane pairs). Rerun -> `downloaded=0 skipped=30` in 1.0s, which also proves the two-pass resume: pass 2 planned from lane artifacts read back from disk. `academy check` -> `unchanged=30 not_downloaded=130` in 18.2s. Real lanes observed: Aulus jungle, Esper Assassin jungle, Marcel roam.

L11. Live verification, hero port: `heroes sync --limit 2` after the refactor -> 17 artifacts in 11.0s and `check` -> `unchanged=17`. Manifest hashes compared against the pre-refactor run: 17/17 identical, so the engine extraction changed no byte of stored data.

L12. Live verification, addon: `addon win-rate --match-now 100 --wr-now 50 --wr-future 60` -> 25 consecutive wins; `addon ip` -> Cochabamba, Bolivia. An invalid target (60 -> 50) originally printed a traceback, so all commands now share one guard that reports `error: <message>` and exits 1.

L13. Full academy run (2026-11-26): `downloaded=1002 failed=0 unavailable=0` in 629.7s. Composition: 9 collection artifacts + 133 x 5 per-hero resources + 328 lane artifacts. 164 lanes across 133 heroes: exp 80, jungle 74, roam 74, mid 58, gold 42 (31 heroes play two lanes). Rerun -> `downloaded=0 skipped=1002` in 10.6s. Integrity script: 1002 artifacts with `len(records) == total`, zero mismatches, zero empty. Coverage script: lane, stats, counters, teammates, trends, builds and win-rate each cover all 133 catalog heroes. On disk: 8.3 MB.

L14. Full `academy check` (2026-11-26): `unchanged=1002 changed=0 new=0 missing=0 not_downloaded=0 failed=0` in 598.5s. The cost is the price of the API sending no ETag or Last-Modified: every artifact must be re-fetched to compare hashes. A local re-hash mode (detect corruption without network) is the obvious future addition.
