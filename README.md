# MLBB Downloader

Download Mobile Legends: Bang Bang data from the [Rone Arena API](https://arena.rone.dev/api) to a local, resumable, hash-verified dataset.

> **Status:** CLI MVP. The heroes domain is implemented end to end. The GUI is planned as the final phase.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Install

```bash
uv sync
```

## Usage

```bash
# Download hero data (skips anything already stored)
uv run mlbb heroes sync

# Only the first two heroes, into a throwaway directory
uv run mlbb heroes sync --limit 2 --output ./data

# Compare remote data against the local manifest (writes nothing)
uv run mlbb heroes check

# Inspect what is stored locally
uv run mlbb status
```

Default output directory is `%APPDATA%/MLBBDownloader/data` on Windows,
`~/Library/Application Support/MLBBDownloader/data` on macOS, and
`$XDG_DATA_HOME/MLBBDownloader/data` on Linux.

## Data layout

```text
data/
├── manifest.json          # every artifact, its hash, size and origin
└── heroes/
    ├── index.json
    └── Miya/
        ├── detail.json
        ├── stats.json
        ├── skill-combos.json
        ├── trends.json
        ├── relations.json
        ├── counters.json
        ├── compatibility.json
        └── wallpapers.json
```

Every artifact stores `{"endpoint", "total", "records"}`. The manifest lets a
re-run skip completed work, and `check` detects changed, new and missing items
without writing anything.

## Design notes

Measured against the live API, not assumed:

- Page size defaults to 12 and caps at 500. Every paged fetch verifies
  `len(records) == total` and fails rather than storing partial data.
- `index` is a 1-based page number; `index=0` returns an empty page with HTTP 200.
- Responses carry no `ETag` or `Last-Modified`, so SHA-256 is the change signal.
- `Accept-Encoding: gzip` is pinned; the API defaults to zstd.
- Payloads are raw upstream records with shapes that differ between list and
  detail endpoints, so no response models are generated.

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
