from __future__ import annotations

import logging
import os
from pathlib import Path

APP_NAME = "ELI LAB AV Translation"
APP_VERSION = "0.2.0"
DEFAULT_CANVAS_WIDTH = 1920
DEFAULT_CANVAS_HEIGHT = 1080
DEFAULT_FPS = 60
OPENGL_REQUIREMENT = 330
VIDEO_DECK_IDS = ("deck_a", "deck_b", "deck_c", "deck_d")

PROJECT_ROOT = Path(__file__).resolve().parent
ICON_PATH = PROJECT_ROOT / "resources" / "icons" / "Icon.ico"

if os.name == "nt":
    _app_data_root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
else:
    _app_data_root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

DATA_DIR = _app_data_root / "ELI LAB" / "AV Translation"
CACHE_DIR = DATA_DIR / "cache"
THUMBNAIL_DIR = CACHE_DIR / "thumbnails"
MEDIA_DB_PATH = DATA_DIR / "media-library.sqlite3"
LOG_DIR = DATA_DIR / "logs"


def ensure_data_directories() -> None:
    for directory in (DATA_DIR, CACHE_DIR, THUMBNAIL_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def configure_logging(level: int = logging.INFO) -> None:
    ensure_data_directories()
    log_file = LOG_DIR / "av-translation.log"
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
        force=True,
    )
