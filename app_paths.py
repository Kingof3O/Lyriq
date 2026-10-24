"""Central filesystem locations for SpotifyLyrics.

Mutable data must never be written next to ``__file__``.  In a PyInstaller
one-file build ``__file__`` points inside the temporary ``_MEIPASS`` folder,
which is deleted when the application exits, losing all user data.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("AppPaths")

APP_NAME = "SpotifyLyrics"
DB_FILENAME = "spotify_lyrics.db"
LEGACY_DB_FILENAME = "lyrics_cache.db"
PORTABLE_FLAG = "portable.flag"
DATA_DIR_ENV = "SPOTIFYLYRICS_DATA_DIR"

_SUBDIRS = ("logs", "lrc", "thumbnails")


def get_install_dir() -> Path:
    """Directory containing the executable (frozen) or this source file (dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def is_portable() -> bool:
    """Portable mode is enabled by placing ``portable.flag`` next to the app."""
    try:
        return (get_install_dir() / PORTABLE_FLAG).is_file()
    except OSError:
        return False


def get_data_dir() -> Path:
    """Resolve the writable data directory.

    Priority: ``SPOTIFYLYRICS_DATA_DIR`` -> portable ``<install>/data`` ->
    ``%LOCALAPPDATA%/SpotifyLyrics`` -> ``~/AppData/Local/SpotifyLyrics``.
    """
    override = os.environ.get(DATA_DIR_ENV, "").strip()
    if override:
        return Path(os.path.expandvars(override)).expanduser().resolve()

    if is_portable():
        return (get_install_dir() / "data").resolve()

    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        return (Path(os.path.expandvars(local_app_data)) / APP_NAME).resolve()
    return (Path.home() / "AppData" / "Local" / APP_NAME).resolve()


def ensure_app_dirs() -> Path:
    """Create the data directory and its subdirectories. Idempotent."""
    data_dir = get_data_dir()
    for name in (None,) + _SUBDIRS:
        path = data_dir if name is None else data_dir / name
        path.mkdir(parents=True, exist_ok=True)
    return data_dir


def _ensure_subdir(name: str) -> Path:
    path = get_data_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    return _ensure_subdir("logs")


def get_lrc_dir() -> Path:
    return _ensure_subdir("lrc")


def get_thumbnails_dir() -> Path:
    return _ensure_subdir("thumbnails")


def _legacy_db_path() -> Optional[Path]:
    """Return the historical beside-``__file__`` database path, if meaningful.

    In a frozen one-file build ``__file__`` lives inside ``_MEIPASS`` and is
    wiped on exit, so there is no legacy database worth importing.
    """
    if getattr(sys, "frozen", False):
        return None
    try:
        return Path(__file__).resolve().parent / LEGACY_DB_FILENAME
    except OSError:
        return None


def _migrate_legacy_db(db_path: Path) -> None:
    """Copy a non-empty legacy database once, never overwriting the new one."""
    if db_path.exists():
        return

    legacy = _legacy_db_path()
    if legacy is None or not legacy.is_file():
        return

    try:
        if legacy.stat().st_size <= 0:
            return
        shutil.copy2(legacy, db_path)
        logger.info("Migrated legacy cache database from %s to %s", legacy, db_path)
    except OSError as exc:
        # A failed one-time migration must not prevent the app from starting.
        logger.warning("Could not migrate legacy cache database %s: %s", legacy, exc)


def get_db_path() -> Path:
    """Full path of the SQLite database, creating the data directory."""
    data_dir = ensure_app_dirs()
    db_path = data_dir / DB_FILENAME
    _migrate_legacy_db(db_path)
    return db_path
