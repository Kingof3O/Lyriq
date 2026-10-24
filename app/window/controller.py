"""Unified WindowController composing geometry, modes, and native interop."""

import logging
import window_state
from .native_win32 import get_hwnd, show_window, toggle_show_hide
from .geometry import GeometryManager
from .modes import ModeManager

logger = logging.getLogger("WindowController")


class WindowController:
    def __init__(self, app):
        self._app = app
        self.geom = GeometryManager(self)
        self.modes = ModeManager(self)

    @property
    def window(self):
        return self._app.window

    @property
    def is_fullscreen(self):
        return self.modes.is_fullscreen

    @property
    def is_mini(self):
        return self.modes.is_mini

    @property
    def is_square(self):
        return self.modes.is_square

    def get_hwnd(self):
        return get_hwnd(self.window)

    def window_is_shown(self):
        try:
            return bool(self.window and self.window.events.shown.is_set())
        except Exception:
            return False

    def on_window_shown(self, *args):
        self.modes.on_window_shown()

    def on_window_moved(self, *args):
        if len(args) >= 2:
            self.geom.on_moved(args[0], args[1])

    def on_window_resized(self, *args):
        if len(args) >= 2:
            self.geom.on_resized(args[0], args[1])

    def current_view_mode(self):
        if self.is_fullscreen:
            return "fullscreen"
        if self.is_mini:
            return "mini"
        if self.is_square:
            return "square"
        return "card"

    def persist_owned(self, values):
        try:
            return window_state.persist_settings(values)
        except Exception as exc:
            logger.warning("Could not persist settings %r: %s", values, exc)
            return False

    def save_window_state(self, include_view_mode=True):
        geo = self.geom.snapshot()
        width, height = window_state.clamp_size(geo.get("width"), geo.get("height"))
        values = {"window_width": width, "window_height": height}
        x, y = geo.get("x"), geo.get("y")
        if x is not None and y is not None:
            x, y = window_state.clamp_position(x, y, width, height)
            values["window_x"] = x
            values["window_y"] = y
        with self.geom.lock:
            self.geom.normal.update({"x": x, "y": y, "width": width, "height": height})
        if include_view_mode:
            values["view_mode"] = self.current_view_mode()
            if self._app._tray_available:
                values["close_to_tray"] = self._app.close_to_tray
        self.persist_owned(values)

    def show_window(self):
        return show_window(self.get_hwnd())

    def toggle_show_hide(self):
        toggle_show_hide(self.get_hwnd())

    def hide_to_tray(self):
        if not self.window:
            return False
        self.geom.cancel_timer()
        self.save_window_state()
        try:
            self.window.hide()
            return True
        except Exception as exc:
            logger.warning("Could not hide window to tray: %s", exc)
            return False

    def on_window_closing(self, *args):
        if self._app._quitting:
            return True
        try:
            self.geom.cancel_timer()
            self.save_window_state()
            if not self._app.close_to_tray or not self._app._tray_available:
                return True
            self.window.hide()
            return False
        except Exception:
            logger.exception("Close-to-tray handler failed")
            return True
