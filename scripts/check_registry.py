"""Validate the hand-written endpoint registry against the live OpenAPI spec.

Usage:
    uv run python scripts/check_registry.py
    uv run python scripts/check_registry.py --openapi https://arena.rone.dev/api/openapi.json

Exit code 0 when the registry covers all non-esports, non-user OpenAPI paths
(or they are explicitly accounted for). Exit code 1 on drift.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mlbb_downloader.domain.registry import DESCRIPTORS  # noqa: E402

OPENAPI_DEFAULT = "https://arena.rone.dev/api/openapi.json"
PARAM_RE = re.compile(r"\{[^}]+\}")

# Paths intentionally not covered by bulk registry yet.
IGNORED_PREFIXES = ("/api/esports/", "/api/user/", "/api/esports/standings/calculate")


def normalize(path: str) -> str:
    p = path.strip()
    if p.startswith("/api"):
        p = p[4:] or "/"
    return PARAM_RE.sub("{x}", p)


def fetch_openapi(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "mlbb-downloader/registry-check"})
    with urlopen(req, timeout=30) as resp:  # noqa: S310 - trusted configured URL
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openapi", default=OPENAPI_DEFAULT)
    parser.add_argument("--json", action="store_true", help="print JSON report")
    args = parser.parse_args()

    spec = fetch_openapi(args.openapi)
    openapi_paths = sorted(spec.get("paths", {}).keys())
    registry_paths = {normalize(d.path) for d in DESCRIPTORS.values()}

    missing: list[str] = []
    ignored: list[str] = []
    covered: list[str] = []
    for path in openapi_paths:
        if path.startswith(IGNORED_PREFIXES):
            ignored.append(path)
            continue
        key = normalize(path)
        if key in registry_paths:
            covered.append(path)
        else:
            missing.append(path)

    report = {
        "openapi": args.openapi,
        "covered": covered,
        "ignored": ignored,
        "missing": missing,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"covered={len(covered)} ignored={len(ignored)} missing={len(missing)}")
        for path in missing:
            print(f"  MISSING {path}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
