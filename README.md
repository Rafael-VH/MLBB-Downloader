# MLBB Downloader

Download Mobile Legends: Bang Bang data from the [Rone Arena API](https://arena.rone.dev/api) to a local, resumable, hash-verified dataset.

> **Status:** CLI maduro + GUI MVP (PySide6). Heroes, academy e imágenes soportan sync/check, reportes, progreso y cancelación cooperativa.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Install

```bash
uv sync
```

## Usage

```bash
# All public data (heroes + academy + images)
uv run mlbb sync
uv run mlbb check
uv run mlbb check --local-only          # rehash local, sin fetch remoto de imágenes

# Heroes: list, detail, stats, relations, wallpapers, rank, positions
uv run mlbb heroes sync
uv run mlbb heroes check
uv run mlbb heroes sync --hero-id 1     # solo un héroe

# Academy: items, spells, emblems, ranks and per-hero win rates
uv run mlbb academy sync
uv run mlbb academy check

# Image assets (discovered from JSON already in the store)
uv run mlbb images sync
uv run mlbb images check
uv run mlbb images check --local-only
uv run mlbb heroes sync --images        # sync JSON + images in one pass

# Reports and local status
uv run mlbb sync --report ./reports/sync.json
uv run mlbb check --report ./reports/check.md
uv run mlbb status --verify

# Addon tools: one-shot, never downloaded in bulk
uv run mlbb addon win-rate --match-now 100 --wr-now 50 --wr-future 60
uv run mlbb addon ip
```

### GUI (MVP)

```bash
uv sync --extra gui
uv run mlbb-gui
```

Default output directory is `%APPDATA%/MLBBDownloader/data` on Windows,
`~/Library/Application Support/MLBBDownloader/data` on macOS, and
`$XDG_DATA_HOME/MLBBDownloader/data` on Linux.

## Data layout

```text
data/
├── manifest.json                    # every artifact, its hash, size and origin
├── _progress.json                   # optional job checkpoint (phase/counters/status)
├── heroes/
│   ├── index.json
│   ├── rank.json
│   ├── positions.json
│   ├── wallpapers-gallery.json
│   └── Miya/
│       ├── detail.json
│       ├── stats.json
│       ├── skill-combos.json
│       ├── trends.json
│       ├── relations.json
│       ├── counters.json
│       ├── compatibility.json
│       └── wallpapers.json
└── academy/
    ├── version.json
    ├── roles.json
    ├── equipment.json
    ├── equipment-expanded.json
    ├── spells.json
    ├── emblems.json
    ├── ranks.json
    └── heroes/
        ├── catalog.json
        ├── filter.json
        └── Miya/
            ├── lane.json
            ├── stats.json
            ├── counters.json
            ├── teammates.json
            ├── trends.json
            ├── builds-gold.json
            └── win-rate-gold.json
```

Every JSON artifact stores `{"endpoint", "total", "records"}`. Image assets are
stored as binary files with SHA-256 hashes in the same manifest. The manifest lets a
re-run skip completed work, and `check` detects changed, new and missing items
without writing anything.

## Download policy

Bulk sync covers game data. A few endpoints are catalogued in
`domain/registry.py` but deliberately excluded:

- **User-generated content** (`/academy/recommended`, `/academy/heroes/{id}/recommended`).
  The global feed reports `total: 10000` and a single hero had 204 builds; the
  detail payload is byte-identical to the list record, so enumerating it would
  multiply the dataset without adding information.
- **Redundant detail** (`/academy/ranks/{rank_id}`). The 29 rank ranges already
  cover 1..9999 and the detail record duplicates the list entry.
- **Discontinued endpoints** (`/academy/heroes/ratings`). The API answers HTTP
  200 with `code: 10407` and `"接口下线"`; this is reported as unavailable, not
  as a failure.

`builds` and `win-rate/timeline` require a lane. The sync reads each hero's
`lane` artifact and requests only the lanes that hero actually plays, instead
of requesting all five blindly.

## Design notes

Measured against the live API, not assumed:

- Page size defaults to 12 and caps at 500. Every paged fetch verifies
  `len(records) == total` and fails rather than storing partial data.
- `index` is a 1-based page number; `index=0` returns an empty page with HTTP 200.
- Responses carry no `ETag` or `Last-Modified`, so SHA-256 is the change signal.
- `Accept-Encoding: gzip` is pinned; the API defaults to zstd.
- Payloads are raw upstream records with shapes that differ between list and
  detail endpoints, so no response models are generated.
- One engine (`usecases/engine.py`) owns resume, atomic writes, hashing and
  reports; domains only declare artifacts to fetch.
- The manifest is flushed every 25 artifacts. A crash can lose at most that
  window of manifest entries; those files are fetched again, never corrupted.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Legal

Unofficial, community-maintained project. Not affiliated with, endorsed by,
sponsored by, or associated with Shanghai Moonton Technology Co., Ltd.
"Mobile Legends: Bang Bang", "MLBB", names, marks, logos, and in-game assets are
trademarks of their respective owners. Data is provided by the Rone Arena API for
informational, educational and analytical purposes.
