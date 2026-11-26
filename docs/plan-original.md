# Plan original (extraído de AGENTS.md)

> Extraído de AGENTS.md para conservar el plan/spec inicial. Para el estado actual y roadmap vigente, ver [plan-maestro.md](plan-maestro.md).

---

# AGENTS.md — MLBB Data Downloader GUI

> Instructions for building a new standalone Python project that downloads Mobile Legends: Bang Bang data from the Rone Arena API, checks for updates/missing files, and ships as a desktop executable.

## 1. Project Goal

Build a desktop GUI application in Python that lets a user:

- Browse the available data tools/endpoints exposed by the Rone Arena API.
- Download **all available MLBB data** (heroes, academy, esports, addons; user endpoints only when explicitly authenticated).
- Download by category or by single entity (for example, one hero).
- Detect missing files, incomplete downloads, and upstream changes/updates.
- Resume interrupted downloads safely.
- Export human-readable indexes (`.md`/`.json`) alongside raw data.
- Package the app as a Windows executable (and optionally macOS/Linux builds).

This project is a **new repository**, separate from `rone-arena-api`. It consumes the public API; it does not modify the API server.

## 2. Source of Truth

- API base URL: `https://arena.rone.dev/api`
- OpenAPI schema: `https://arena.rone.dev/api/openapi.json`
- Swagger UI: `https://arena.rone.dev/api/docs`
- Existing reference exporter in the API repo: `scripts/fetch_hero_assets.py`

Do not hardcode assumptions when the OpenAPI/schema can be read. Generate or maintain an endpoint catalog from the API docs where practical.

## 3. Legal / Attribution / Safety

- Keep the disclaimer visible in the app About screen and README:
  - Unofficial, community-maintained project.
  - Not affiliated with, endorsed by, sponsored by, or associated with Moonton.
  - Mobile Legends: Bang Bang, MLBB, names, marks, logos, and in-game assets are trademarks of their respective owners.
- Attribute data sources appropriately:
  - Game data from Rone Arena API / publicly available game services.
  - Esports data from official MPL Indonesia, Philippines, Malaysia, and Cambodia public sites as surfaced by the API.
- Do not embed secrets, private upstream keys, or user JWTs in source.
- Respect rate limits/WAF behavior: sequential requests, bounded retries, backoff on 403/405/429/5xx.
- Do not hammer the API. Default delay between requests should be configurable (safe default >= 0.35s).
- User auth tokens must be stored only if the user explicitly opts in; prefer OS keyring or encrypted local storage. Never log tokens.

## 4. Recommended Tech Stack

| Area | Recommendation | Why |
| --- | --- | --- |
| Language | Python 3.12+ | Matches modern packaging and typing |
| GUI | PySide6 (Qt) | Mature widgets, QThread/QProcess, good Windows packaging |
| HTTP | `httpx` | Sync/async support, timeout/retry control, typed responses |
| Models | `pydantic` v2 | Validate API payloads and local manifests |
| CLI | `typer` or `argparse` | Headless automation/debug mode |
| Logging | `logging` + rotating file handler | Debuggable downloads |
| Packaging | PyInstaller | Simple Windows `.exe` output |
| Tests | `pytest` | Unit/integration tests |
| Lint/format | `ruff` | Fast lint + format |
| Project manager | `uv` | Reproducible env and lockfile |

Alternative GUI: `customtkinter` for a lighter dependency, but PySide6 is preferred for long-term maintainability and background worker support.

## 5. Repository Layout

```text
mlbb-downloader-gui/
├── AGENTS.md
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── src/
│   └── mlbb_downloader/
│       ├── __init__.py
│       ├── app.py                  # GUI entrypoint
│       ├── cli.py                  # optional CLI entrypoint
│       ├── config.py               # settings, paths, defaults
│       ├── api/
│       │   ├── client.py           # httpx client, retries, throttling
│       │   ├── endpoints.py        # endpoint catalog / registry
│       │   └── models.py           # pydantic response models
│       ├── downloaders/
│       │   ├── base.py             # downloader contract
│       │   ├── heroes.py
│       │   ├── academy.py
│       │   ├── esports.py
│       │   ├── addon.py
│       │   └── user.py             # auth-gated, explicit opt-in
│       ├── storage/
│       │   ├── manifest.py         # manifest read/write
│       │   ├── paths.py
│       │   └── integrity.py        # hashes, size checks, missing files
│       ├── services/
│       │   ├── update_check.py     # compare remote vs local manifest
│       │   ├── scheduler.py         # job queue
│       │   └── report.py           # markdown/json reports
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── widgets/
│       │   ├── workers.py          # QThread/QRunnable workers
│       │   └── assets/
│       └── utils/
│           ├── slug.py
│           ├── time.py
│           └── fs.py
├── tests/
│   ├── test_manifest.py
│   ├── test_update_check.py
│   ├── test_heroes_downloader.py
│   └── fixtures/
└── docs/
    └── screenshots/
```

## 6. API Coverage Map

The GUI should expose tools grouped by API domain. Start with public, non-auth domains.

### 6.1 Heroes (`/api/heroes`)

| Tool | Endpoint | Output |
| --- | --- | --- |
| List heroes | `GET /heroes` | `heroes/index.json`, `heroes/index.md` |
| Hero rank | `GET /heroes/rank` | `heroes/rank/{date-or-snapshot}.json` |
| Position filters | `GET /heroes/positions` | `heroes/positions.json` |
| Hero detail | `GET /heroes/{id}` | `heroes/{name}/detail.json`, `hero.md` |
| Hero stats | `GET /heroes/{id}/stats` | `heroes/{name}/stats.json` |
| Skill combos | `GET /heroes/{id}/skill-combos` | `heroes/{name}/skill-combos.json` |
| Trends | `GET /heroes/{id}/trends` | `heroes/{name}/trends.json` |
| Relations | `GET /heroes/{id}/relations` | `heroes/{name}/relations.json` |
| Counters | `GET /heroes/{id}/counters` | `heroes/{name}/counters.json` |
| Compatibility | `GET /heroes/{id}/compatibility` | `heroes/{name}/compatibility.json` |
| Hero wallpapers | `GET /heroes/{id}/wallpapers` | `heroes/{name}/wallpaper-*.jpg/png` |
| Wallpapers gallery | `GET /heroes/wallpapers` | `heroes/wallpapers-gallery.json` |

Image assets to download when present: hero icon/head, splash/painting, skill icons, wallpapers (desktop/mobile exact resolutions where available).

### 6.2 Academy (`/api/academy`)

Cover all academy endpoints exposed by OpenAPI, including:

- meta/version
- heroes/catalog
- roles
- equipment, equipment/expanded
- spells
- emblems
- ranks, ranks/{rank_id}
- recommended
- builds-related endpoints
- lane heroes / win-rate timeline / ratings / trends / matchups / stats as available in current API

Implementation rule: build the academy tool list from OpenAPI at startup or from a generated endpoint registry checked into the repo. Do not hand-maintain a stale list.

### 6.3 Esports (`/api/esports`)

Cover leagues: `id`, `ph`, `my`, `kh`.

Per league where available:

- schedule, playoffs, standings
- matches/{id-or-slug}
- teams, teams/{team_id}
- statistics/teams, statistics/players, statistics/heroes
- league-specific extras: hero-pools, player-pools, mvp, savage-maniac, players, images

Also include simulator endpoints as tools (not bulk downloads): `POST /{league}/standings/simulate`, `POST /standings/calculate`.

### 6.4 Addon (`/api/addon`)

- win-rate-calculator (interactive tool)
- ip location (interactive tool; do not bulk-download)

### 6.5 User (`/api/user`) — Auth-gated

Only enable when user provides roleId, zoneId, and verification flow/JWT as required by API. Default: disabled.

- send-vc, login, logout
- info, stats, privacy settings
- season, matches, match detail
- frequent heroes, matches by hero, friends

User data contains personal information. Require explicit confirmation before download. Store separately under `data/user/{roleId}-{zoneId}/` and exclude from "Download All" unless the user checks "Include authenticated user data".

## 7. Core Features

### 7.1 Download All

A top-level button runs a orchestrated job:

1. Load endpoint catalog.
2. Read local manifest.
3. Create a download plan (new, changed, missing, unchanged).
4. Execute by category with concurrency limited to safe sequential/low-parallel settings.
5. Save raw JSON, assets, markdown indexes, and manifest.
6. Show summary: downloaded, skipped, failed, missing, elapsed time.

### 7.2 Check Updates / Missing Files

A top-level "Check Updates" button performs a dry-run:

- Compare remote metadata to local manifest.
- Detect missing files referenced by manifest.
- Detect changed payloads using ETag/Last-Modified if available, otherwise content hash.
- Detect new heroes/entities not present locally.
- Produce a report without downloading unless user confirms.

### 7.3 Per-Tool Actions

Each tool card/row should have:

- `Run` / `Download`
- `Check`
- `Open output folder`
- `View last report`
- `Export JSON/MD`

### 7.4 Resume & Checkpoint

- Write `manifest.json` atomically.
- Write `_progress.json` or per-job checkpoint.
- Save file as `.part` then rename on success.
- On restart, skip completed items whose hash/size matches manifest.

### 7.5 Logging & Errors

- UI log panel with level filter.
- Rotating log file under app data dir.
- Error summary with retry button.
- Never crash the GUI thread; workers report errors through signals.

## 8. Update Detection Model

Use a local manifest per output root:

```json
{
  "schema_version": 1,
  "generated_at": "2026-11-26T00:00:00Z",
  "base_url": "https://arena.rone.dev/api",
  "items": {
    "heroes/detail/1": {
      "endpoint": "/heroes/1",
      "etag": null,
      "last_modified": null,
      "sha256": "...",
      "size": 12345,
      "path": "heroes/Miya/detail.json",
      "downloaded_at": "..."
    }
  }
}
```

Update rules:

- **Missing**: manifest entry exists but file missing, or remote entity exists but no local entry.
- **Changed**: hash differs, or ETag/Last-Modified changed, or key fields changed (e.g., hero count, patch version).
- **Unchanged**: metadata/hash matches.
- **New**: entity appears remotely but not locally.

For images, store URL, resolved filename, content-type, size, and sha256.

## 9. GUI Design

### 9.1 Main Window

- Left sidebar: categories (Dashboard, Heroes, Academy, Esports, Addon, User, Settings, Logs).
- Top bar: base URL, output folder, "Check Updates", "Download All", "Pause/Resume", "Cancel".
- Main content: tool cards/table with status, last run, items, missing, changed.
- Bottom status bar: current job, progress bar, request count, errors.

### 9.2 Dashboard

- Total entities downloaded.
- Missing files count.
- Updates available.
- Last full sync.
- Disk usage.
- Quick actions.

### 9.3 Settings

- Base URL (default official API).
- Output directory.
- Request delay, timeout, retries.
- User-Agent toggle (safe default).
- Include images / include raw JSON / include markdown.
- Auth settings for user endpoints (opt-in).
- Proxy support (optional).

## 10. Executable Packaging

Use PyInstaller:

```bash
uv run pyinstaller --noconfirm --clean --name MLBBDownloader \
  --windowed --onefile src/mlbb_downloader/app.py
```

Windows notes:

- Test on clean Windows VM without Python installed.
- Include Qt plugins/assets.
- Sign executable if certificate is available (optional).
- Put logs/config in `%APPDATA%/MLBBDownloader/`, not next to exe.

## 11. Testing Strategy

- Unit tests for manifest, path sanitization, update diff, retry/backoff, filename resolution.
- Integration tests with mocked HTTP responses (`respx` or `httpx.MockTransport`).
- GUI smoke test: app launches, main window renders, worker can be started/cancelled.
- Golden fixtures for sample hero/academy payloads.
- Do not hit the live API in CI by default; provide an opt-in `LIVE_API_TESTS=1` mode.

## 12. CI / Release

- `ci.yml`: lint, format check, tests, pyinstaller build smoke.
- `release.yml`: on tag `v*`, build Windows exe, generate checksums, attach to GitHub Release.
- Semantic versioning.
- Keep changelog in `CHANGELOG.md`.

## 13. Implementation Milestones

1. **Foundation**: repo scaffold, config, httpx client, manifest, logging.
2. **Heroes MVP**: hero list/detail/assets/wallpapers, check updates, resume.
3. **Academy + Addon**: endpoint registry-driven downloads.
4. **Esports**: leagues, teams, matches, stats, images.
5. **GUI polish**: dashboard, workers, progress, cancel/pause.
6. **Auth/User optional**: explicit opt-in user data download.
7. **Packaging/release**: PyInstaller, CI, GitHub Release.

## 14. Acceptance Criteria

- User can click "Download All" and get a complete local dataset for public endpoints.
- User can click "Check Updates" and see new/changed/missing items without downloading.
- Interrupted downloads can resume without corrupting files.
- No secrets/tokens are written to logs.
- App runs as a packaged Windows executable.
- README includes setup, usage, legal disclaimer, and attribution.

## 15. Agent Working Rules

- Before coding, read this AGENTS.md and the target repo README.
- Prefer small, reviewable commits by work unit.
- Do not add dependencies without justification.
- Keep UI responsive: no blocking HTTP calls on the GUI thread.
- Every downloader must be idempotent.
- Every new endpoint/tool must have: manifest entry, output path rule, check-update support, and test coverage.
- If an endpoint requires auth or has special rate limits, document it in code and UI.
- Before release, verify executable on a clean environment and run the full test suite.
