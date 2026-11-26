"""Application settings and platform paths."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "MLBBDownloader"

DEFAULT_BASE_URL = "https://arena.rone.dev/api"
DEFAULT_PAGE_SIZE = 500
DEFAULT_DELAY = 0.35
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3


def app_data_dir() -> Path:
    """Return the per-user application data directory."""
    if os.name == "nt":
        root = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(root) / APP_NAME


def default_output_dir() -> Path:
    return app_data_dir() / "data"


def gui_settings_path() -> Path:
    return app_data_dir() / "gui-settings.json"


@dataclass(slots=True)
class Settings:
    base_url: str = DEFAULT_BASE_URL
    output_dir: Path = field(default_factory=default_output_dir)
    page_size: int = DEFAULT_PAGE_SIZE
    delay: float = DEFAULT_DELAY
    timeout: float = DEFAULT_TIMEOUT
    retries: int = DEFAULT_RETRIES
    include_images: bool = False
    language: str = "en"

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        if self.page_size < 1:
            raise ValueError("page_size must be positive")
        if self.delay < 0:
            raise ValueError("delay must be non-negative")


def load_gui_settings() -> dict[str, object]:
    path = gui_settings_path()
    if not path.exists():
        return {}
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_gui_settings(data: dict[str, object]) -> None:
    import json

    path = gui_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"{path.name}.part")
    partial.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(partial, path)
