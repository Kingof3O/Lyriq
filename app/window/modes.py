"""Window mode transitions: Mini Island, 1:1 Square, and Fullscreen."""

import logging
import window_state
from .native_win32 import update_native_min_size

logger = logging.getLogger("ModeManager")
MINI_HEIGHT = 95


class ModeManager:
    def __init__(self, controller):
        self.ctrl = controller
        self.mini_width = window_state.DEFAULT_MINI_WIDTH
        self.mini_expanded = False
        self.is_mini = False

        self.square_size = window_state.DEFAULT_SQUARE_SIZE
        self.is_square = False

        self.is_fullscreen = False

        self.pending_mini = False
        self.pending_square = False
        self.pending_fullscreen = False

    def on_window_shown(self):
        w = self.ctrl.window
        try:
            if self.pending_mini and self.is_mini and w:
                self.pending_mini = False
                update_native_min_size(w, window_state.MIN_MINI_WIDTH, 85)
                curr_h = 270 if self.mini_expanded else MINI_HEIGHT
                w.resize(self.mini_width, curr_h)
            if self.pending_square and self.is_square and w:
                self.pending_square = False
                update_native_min_size(
                    w, window_state.MIN_SQUARE_SIZE, window_state.MIN_SQUARE_SIZE
                )
                w.resize(self.square_size, self.square_size)
            if self.pending_fullscreen and self.is_fullscreen and w:
                self.pending_fullscreen = False
                w.toggle_fullscreen()
        except Exception:
            logger.exception("Could not apply pending window mode")

    def set_mini_mode(self, enabled):
        enabled = bool(enabled)
        if enabled == self.is_mini:
            return
        self.ctrl.geom.capture_normal()
        if enabled and self.is_fullscreen:
            self.is_fullscreen = False
            self.pending_fullscreen = False
            try:
                if self.ctrl.window and self.ctrl.window_is_shown():
                    self.ctrl.window.toggle_fullscreen()
            except Exception as exc:
                logger.warning("Could not leave fullscreen for mini: %s", exc)

        self.is_mini = enabled
        self.ctrl.geom.ignore_for()
        w = self.ctrl.window
        if enabled:
            if self.is_square:
                self.is_square = False
                self.pending_square = False
            update_native_min_size(w, window_state.MIN_MINI_WIDTH, 85)
            if w and self.ctrl.window_is_shown():
                try:
                    curr_h = 270 if self.mini_expanded else MINI_HEIGHT
                    w.resize(self.mini_width, curr_h)
                except Exception as exc:
                    logger.warning("Could not resize mini mode: %s", exc)
            else:
                self.pending_mini = True
        else:
            self.pending_mini = False
            update_native_min_size(w, window_state.MIN_WIDTH, window_state.MIN_HEIGHT)
            geo = dict(self.ctrl.geom.normal)
            width, height = window_state.clamp_size(geo.get("width"), geo.get("height"))
            with self.ctrl.geom.lock:
                self.ctrl.geom.normal["width"] = width
                self.ctrl.geom.normal["height"] = height
            if w and self.ctrl.window_is_shown():
                try:
                    x, y = geo.get("x"), geo.get("y")
                    if x is not None and y is not None:
                        w.move(int(x), int(y))
                    w.resize(width, height)
                except Exception as exc:
                    logger.warning("Could not restore normal window: %s", exc)

        self.ctrl.persist_owned({"view_mode": "mini" if enabled else "card"})

    def set_mini_expand(self, is_expanded):
        self.mini_expanded = bool(is_expanded)
        w = self.ctrl.window
        if w and self.is_mini and self.ctrl.window_is_shown():
            try:
                curr_h = 270 if is_expanded else MINI_HEIGHT
                w.resize(self.mini_width, curr_h)
            except Exception as exc:
                logger.warning("Could not toggle mini expand: %s", exc)

    def set_mini_width(self, width):
        clamped = window_state.clamp_mini_width(width)
        self.mini_width = clamped
        w = self.ctrl.window
        if w and self.is_mini and self.ctrl.window_is_shown():
            try:
                curr_h = 270 if self.mini_expanded else MINI_HEIGHT
                w.resize(clamped, curr_h)
            except Exception as exc:
                logger.warning("Could not resize mini width: %s", exc)
        self.ctrl.persist_owned({"mini_width": clamped})
        return clamped

    def set_square_mode(self, enabled):
        enabled = bool(enabled)
        if enabled == self.is_square:
            return
        if not self.is_mini:
            self.ctrl.geom.capture_normal()
        if enabled and self.is_fullscreen:
            self.is_fullscreen = False
            self.pending_fullscreen = False
            try:
                if self.ctrl.window and self.ctrl.window_is_shown():
                    self.ctrl.window.toggle_fullscreen()
            except Exception as exc:
                logger.warning("Could not leave fullscreen for square: %s", exc)
        if enabled and self.is_mini:
            self.is_mini = False
            self.pending_mini = False

        self.is_square = enabled
        self.ctrl.geom.ignore_for()
        w = self.ctrl.window
        if enabled:
            update_native_min_size(
                w, window_state.MIN_SQUARE_SIZE, window_state.MIN_SQUARE_SIZE
            )
            if w and self.ctrl.window_is_shown():
                try:
                    w.resize(self.square_size, self.square_size)
                except Exception as exc:
                    logger.warning("Could not resize square mode: %s", exc)
            else:
                self.pending_square = True
        else:
            self.pending_square = False
            update_native_min_size(w, window_state.MIN_WIDTH, window_state.MIN_HEIGHT)
            geo = dict(self.ctrl.geom.normal)
            width, height = window_state.clamp_size(geo.get("width"), geo.get("height"))
            with self.ctrl.geom.lock:
                self.ctrl.geom.normal["width"] = width
                self.ctrl.geom.normal["height"] = height
            if w and self.ctrl.window_is_shown():
                try:
                    x, y = geo.get("x"), geo.get("y")
                    if x is not None and y is not None:
                        w.move(int(x), int(y))
                    w.resize(width, height)
                except Exception as exc:
                    logger.warning("Could not restore normal window: %s", exc)

        self.ctrl.persist_owned({"view_mode": "square" if enabled else "card"})

    def set_square_size(self, size):
        clamped = window_state.clamp_square_size(size)
        self.square_size = clamped
        w = self.ctrl.window
        if w and self.is_square and self.ctrl.window_is_shown():
            try:
                w.resize(clamped, clamped)
            except Exception as exc:
                logger.warning("Could not resize square window: %s", exc)
        self.ctrl.persist_owned({"square_size": clamped})
        return clamped

    def set_fullscreen_mode(self, enabled):
        enabled = bool(enabled)
        if enabled == self.is_fullscreen:
            return
        if enabled:
            if self.is_mini:
                self.is_mini = False
                self.pending_mini = False
            elif self.is_square:
                self.is_square = False
                self.pending_square = False
            else:
                self.ctrl.geom.capture_normal()
        self.is_fullscreen = enabled
        self.ctrl.geom.ignore_for()
        w = self.ctrl.window
        if w and self.ctrl.window_is_shown():
            try:
                w.toggle_fullscreen()
            except Exception as exc:
                logger.warning("Could not toggle fullscreen: %s", exc)
        else:
            self.pending_fullscreen = enabled

        if not enabled and w and self.ctrl.window_is_shown() and not self.is_mini:
            try:
                width, height = window_state.clamp_size(
                    self.ctrl.geom.normal.get("width"),
                    self.ctrl.geom.normal.get("height"),
                )
                w.resize(width, height)
            except Exception as exc:
                logger.warning("Could not restore size after fullscreen: %s", exc)

        view_mode = (
            "fullscreen"
            if enabled
            else ("mini" if self.is_mini else ("square" if self.is_square else "card"))
        )
        self.ctrl.persist_owned({"view_mode": view_mode})
