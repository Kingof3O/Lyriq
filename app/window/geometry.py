"""Window geometry tracking, debouncing, and clamping."""

import logging
import threading
import time
import window_state

logger = logging.getLogger("GeometryManager")


class GeometryManager:
    def __init__(self, controller):
        self.ctrl = controller
        self.lock = threading.Lock()
        self.timer = None
        self.ignore_until = 0.0
        self.normal = {
            "x": None,
            "y": None,
            "width": window_state.DEFAULT_WIDTH,
            "height": window_state.DEFAULT_HEIGHT,
        }

    def ignore_for(self, seconds=0.8):
        self.ignore_until = time.monotonic() + seconds

    def events_allowed(self):
        return (
            not self.ctrl._app._quitting
            and not self.ctrl.is_mini
            and not self.ctrl.is_square
            and not self.ctrl.is_fullscreen
            and time.monotonic() >= self.ignore_until
        )

    def capture_normal(self):
        if self.ctrl.is_mini or self.ctrl.is_fullscreen or self.ctrl.is_square:
            return
        geo = self.snapshot()
        w, h = window_state.clamp_size(geo.get("width"), geo.get("height"))
        if w >= window_state.MIN_WIDTH and h >= window_state.MIN_HEIGHT:
            geo["width"] = w
            geo["height"] = h
            with self.lock:
                self.normal = geo

    def snapshot(self):
        with self.lock:
            geo = dict(self.normal)
        w = self.ctrl.window
        if (
            w
            and not self.ctrl.is_mini
            and not self.ctrl.is_square
            and not self.ctrl.is_fullscreen
            and self.ctrl.window_is_shown()
        ):
            try:
                geo.update(
                    {
                        "x": int(w.x),
                        "y": int(w.y),
                        "width": int(w.width),
                        "height": int(w.height),
                    }
                )
            except Exception as exc:
                logger.debug("Could not read live window geometry: %s", exc)
        return geo

    def on_moved(self, x, y):
        if not self.events_allowed():
            return
        try:
            with self.lock:
                self.normal["x"] = int(x)
                self.normal["y"] = int(y)
            self.schedule_save()
        except (TypeError, ValueError):
            pass

    def on_resized(self, width, height):
        if not self.events_allowed():
            return
        try:
            w, h = int(width), int(height)
            if w <= 0 or h <= 0:
                return
            with self.lock:
                self.normal["width"] = w
                self.normal["height"] = h
            self.schedule_save()
        except (TypeError, ValueError):
            pass

    def schedule_save(self):
        if self.ctrl._app._quitting:
            return
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
            t = threading.Timer(1.0, self._flush)
            t.daemon = True
            self.timer = t
            t.start()

    def _flush(self):
        with self.lock:
            self.timer = None
        if not self.events_allowed():
            return
        self.ctrl.save_window_state(include_view_mode=False)

    def cancel_timer(self):
        with self.lock:
            t = self.timer
            self.timer = None
        if t is not None:
            t.cancel()
