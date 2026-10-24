"""Window geometry and companion settings persistence.

The cache is the single source of truth for persisted settings.  The frontend
also writes some of the keys owned here (``always_on_top`` and ``view_mode``),
so updates are deliberately limited to the keys that changed and never write a
stale snapshot of the whole settings dictionary.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging

from cache_service import get_cache

logger = logging.getLogger("WindowState")

DEFAULT_WIDTH = 480
DEFAULT_HEIGHT = 720
MIN_WIDTH = 360
MIN_HEIGHT = 85

# Keys this module (and main.py) is allowed to write.  Everything else belongs
# to the frontend and must not be copied back from a stale snapshot.
OWNED_SETTING_KEYS = frozenset(
    {
        "window_x",
        "window_y",
        "window_width",
        "window_height",
        "always_on_top",
        "close_to_tray",
        "view_mode",
        "start_with_windows",
    }
)

_SM_XVIRTUALSCREEN = 76
_SM_YVIRTUALSCREEN = 77
_SM_CXVIRTUALSCREEN = 78
_SM_CYVIRTUALSCREEN = 79
_SPI_GETWORKAREA = 0x0030


def _as_int(value, default=None):
    if value is None or isinstance(value, bool):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default


def clamp_size(width, height):
    """Return a usable window size, falling back to the app defaults."""
    width = _as_int(width, DEFAULT_WIDTH)
    height = _as_int(height, DEFAULT_HEIGHT)
    if width <= 0:
        width = DEFAULT_WIDTH
    if height <= 0:
        height = DEFAULT_HEIGHT
    return max(MIN_WIDTH, width), max(MIN_HEIGHT, height)


def _virtual_screen():
    try:
        user32 = ctypes.WinDLL("user32")
        rect = (
            user32.GetSystemMetrics(_SM_XVIRTUALSCREEN),
            user32.GetSystemMetrics(_SM_YVIRTUALSCREEN),
            user32.GetSystemMetrics(_SM_CXVIRTUALSCREEN),
            user32.GetSystemMetrics(_SM_CYVIRTUALSCREEN),
        )
        if rect[2] > 0 and rect[3] > 0:
            return rect
    except Exception as exc:
        logger.debug("Could not read virtual screen bounds: %s", exc)
    return (0, 0, 1920, 1080)


def _work_area():
    try:
        user32 = ctypes.WinDLL("user32")
        rect = ctypes.wintypes.RECT()
        if user32.SystemParametersInfoW(
            _SPI_GETWORKAREA, 0, ctypes.byref(rect), 0
        ):
            return (
                rect.left,
                rect.top,
                max(1, rect.right - rect.left),
                max(1, rect.bottom - rect.top),
            )
    except Exception as exc:
        logger.debug("Could not read the primary work area: %s", exc)
    return (0, 0, 1920, 1080)


def center_position(width, height):
    left, top, area_width, area_height = _work_area()
    width, height = clamp_size(width, height)
    x = left + max(0, (area_width - width) // 2)
    y = top + max(0, (area_height - height) // 2)
    return x, y


def clamp_position(x, y, width, height):
    """Keep a saved position within the virtual desktop.

    A window is fully pulled back on screen when it fits; oversized windows are
    anchored to the virtual desktop origin.  Positions that no longer overlap
    the desktop (unplugged monitor, resolution change) are re-centered on the
    primary work area.
    """
    width, height = clamp_size(width, height)
    x = _as_int(x)
    y = _as_int(y)
    if x is None or y is None:
        return center_position(width, height)

    vx, vy, vw, vh = _virtual_screen()
    horizontal_visible = min(80, width)
    vertical_visible = min(40, height)
    if (
        x + width < vx + horizontal_visible
        or x > vx + vw - horizontal_visible
        or y + height < vy + vertical_visible
        or y > vy + vh - vertical_visible
    ):
        return center_position(width, height)

    if width <= vw:
        x = min(max(x, vx), vx + vw - width)
    else:
        x = vx

    if height <= vh:
        y = min(max(y, vy), vy + vh - height)
    else:
        y = vy
    return x, y


def load_window_settings(settings):
    """Build validated window settings from a persisted settings mapping."""
    settings = settings if isinstance(settings, dict) else {}
    width, height = clamp_size(
        settings.get("window_width"), settings.get("window_height")
    )

    x = _as_int(settings.get("window_x"))
    y = _as_int(settings.get("window_y"))
    if x is None or y is None:
        x, y = None, None
    else:
        x, y = clamp_position(x, y, width, height)

    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "always_on_top": bool(settings.get("always_on_top", False)),
        "close_to_tray": bool(settings.get("close_to_tray", True)),
        "view_mode": settings.get("view_mode", "card"),
    }


def persist_settings(changes):
    """Persist only known keys and only when their value actually changed."""
    if not isinstance(changes, dict):
        return False
    allowed = {
        key: value
        for key, value in changes.items()
        if key in OWNED_SETTING_KEYS
    }
    if not allowed:
        return False

    try:
        cache = get_cache()
        current = cache.get_settings()

        if "window_width" in allowed or "window_height" in allowed:
            width, height = clamp_size(
                allowed.get("window_width", current.get("window_width")),
                allowed.get("window_height", current.get("window_height")),
            )
            if "window_width" in allowed:
                allowed["window_width"] = width
            if "window_height" in allowed:
                allowed["window_height"] = height

        if "window_x" in allowed or "window_y" in allowed:
            x = _as_int(allowed.get("window_x", current.get("window_x")))
            y = _as_int(allowed.get("window_y", current.get("window_y")))
            if x is not None and y is not None:
                width, height = clamp_size(
                    allowed.get("window_width", current.get("window_width")),
                    allowed.get("window_height", current.get("window_height")),
                )
                x, y = clamp_position(x, y, width, height)
                if "window_x" in allowed:
                    allowed["window_x"] = x
                if "window_y" in allowed:
                    allowed["window_y"] = y

        patch = {
            key: value
            for key, value in allowed.items()
            if current.get(key) != value
        }
        if not patch:
            return True
        return bool(cache.set_settings(patch))
    except Exception as exc:
        logger.warning("Could not persist window settings: %s", exc)
        return False
