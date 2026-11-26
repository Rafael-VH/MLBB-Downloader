# Layered architecture â€” domain / adapters / usecases / cli

Branch: `feat/academy-addon` Â· Delivery: work-unit commits (4) Â· Runner: `uv run pytest -q`

## Specs

- **S1** `src/mlbb_downloader/domain/` is pure: no `httpx`, no `typer`, no `mlbb_downloader.adapters`,
  no `mlbb_downloader.usecases`, no filesystem writes. `pydantic` is allowed (validation only).
- **S2** Dependency direction is `domain` <- `adapters` <- `usecases` <- `cli`. No cycles.
- **S3** Zero behaviour change: the 59 existing tests stay green with import-path edits only.
  No test assertion is modified, deleted, or weakened.
- **S4** `local_entity_ids` accepts a `Manifest`, not a `DataStore`, so identity stays in `domain`.
- **S5** `tests/test_architecture.py` fails when `domain/*.py` imports a banned module.
- **S6** Four commits, one per stage; the full suite passes after each.

## Tasks

| ID | Spec | Route | Status | Commit |
| -- | ---- | ----- | ------ | ------ |
| T1 | S1 S2 S3 S4 | inline | done | `212d91d` |
| T2 | S1 S2 S3 | inline | done | `116cf51` |
| T3 | S2 S3 | inline | done | `fba1984` |
| T4 | S1 S5 S6 | inline | done | `722d2eb` |

### T1 â€” split the manifest
`domain/manifest.py` (ManifestItem, Manifest) + `domain/keying.py` (item_key, hero_identity,
local_entity_ids) + `adapters/manifest_store.py` (ManifestStore). Remove `storage/manifest.py`
and `downloaders/identity.py`.

### T2 â€” move the pure modules
`api/registry.py` -> `domain/registry.py`; `utils/slug.py` -> `domain/layout.py`. Drop `utils/`.

### T3 â€” move the adapters
`api/client.py` -> `adapters/arena.py`; `storage/store.py` -> `adapters/fsstore.py`;
`storage/paths.py` -> `adapters/paths.py`; `api/errors.py` -> `errors.py`. Drop `api/`, `storage/`.

### T4 â€” move the use cases
`downloaders/*` -> `usecases/*`; `addon.py` -> `usecases/addon.py`. Drop `downloaders/`.
Add `tests/test_architecture.py`.

## Log

- **L1** (user, verbatim): "Si y verifica que el plan original pueda funcionar con el estado actual del
  proyecto y si necesita ser modificado avÃ­same que vas a modificar y espera mi aprobaciÃ³n."
  Followed by approval of the reported corrections: "Si".
- **L2** Verification found two real plan corrections: `item_key` lives in `storage/manifest.py`, not
  `downloaders/identity.py`; and `local_entity_ids(store)` must take a `Manifest` to keep `domain` pure.
  `storage/paths.py` is adapter code (it calls `Path.resolve()` and validates containment).
  `api/errors.py` has 5 test consumers, not 1.
- **L3** `__init__.py` of `api/`, `storage/`, `downloaders/` are empty, so package removal is clean.
