import os
import sys
import json
import logging
import math
import time
import threading
import ctypes
import ctypes.wintypes
import urllib.parse
import urllib.request
import webview

import app_paths
import lyrics_providers
import startup
import window_state
from media_listener import MediaListener
from lyrics_service import LyricsService
from translator_service import TranslatorService
from romanizer import Romanizer
from discord_rpc import DiscordRPC
from cache_service import get_cache
from single_instance import SingleInstance
from tray_icon import TrayIcon

logger = logging.getLogger("Lyriq")

APP_TITLE = "Lyriq"
TRAY_TOOLTIP = "Lyriq"
MINI_WIDTH = 560
MINI_HEIGHT = 54


from hotkey_listener import HotkeyThread
from api_bridge import AppAPI, _make_track_key

user32 = ctypes.windll.user32

# Defensive patch for pywebview winforms BrowserForm.move:
# Pywebview's winforms implementation passes None for cx and cy in SetWindowPos,
# which fails on Python 3.12 64-bit if user32.SetWindowPos.argtypes enforces c_int.
# We patch it safely here so window dragging and positioning never throw ctypes ArgumentError.
try:
    import webview.platforms.winforms as _winforms_platform
    def _patched_browserform_move(self, x, y):
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_SHOWWINDOW = 0x0040
        scale = getattr(self, "_scale", 1)
        if scale != 1:
            x_phys = int(x * scale)
            y_phys = int(y * scale)
        else:
            x_phys = int(x)
            y_phys = int(y)
        ctypes.windll.user32.SetWindowPos(
            self.Handle.ToInt32(),
            0,
            x_phys,
            y_phys,
            0,
            0,
            SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW,
        )
    _winforms_platform.BrowserView.BrowserForm.move = _patched_browserform_move
except Exception as _patch_exc:
    logger.debug("Could not patch BrowserForm.move: %s", _patch_exc)


class SpotifyLyricsApp:
    def __init__(self, start_minimized=False):
        self.lyrics_service = LyricsService()
        self.translator_service = TranslatorService(target_lang="en")
        self.media_listener = None
        self.window = None
        self.hotkey_thread = None
        self.discord_rpc = DiscordRPC(self.lyrics_service.cache.get_setting("discord_client_id", ""))

        self.start_minimized = bool(start_minimized)
        self.tray = None
        self._tray_available = False
        self.single_instance = None
        self.close_to_tray = True

        # Geometry is tracked separately from mini/fullscreen so the normal
        # window shape survives those modes.
        self._normal_geometry = {
            "x": None,
            "y": None,
            "width": window_state.DEFAULT_WIDTH,
            "height": window_state.DEFAULT_HEIGHT,
        }
        self._geometry_timer = None
        self._geometry_lock = threading.Lock()
        self._ignore_geometry_until = 0.0
        self._mini_width = window_state.DEFAULT_MINI_WIDTH
        self._mini_expanded = False
        self._is_mini = False
        self._square_size = window_state.DEFAULT_SQUARE_SIZE
        self._is_square = False
        self._is_fullscreen = False
        self._pending_mini = False
        self._pending_square = False
        self._pending_fullscreen = False
        self._force_show_on_loaded = False

        self._quit_lock = threading.Lock()
        self._quit_running = False
        self._quit_requested = False
        self._quit_done = False
        self._quit_finished = threading.Event()
        self._quitting = False
        self.running = False

        self.current_track = None
        self.current_artist = ""
        self.current_title = ""
        self.current_duration = 0.0
        self.current_lyrics_key = None
        self.last_sync_time = 0
        self.last_position = 0
        self.playback_status = 0

        # Guards generation/track state only; never held during network calls.
        self.state_lock = threading.Lock()
        self.current_generation_id = 0

        # The webview starts after the media listener.  Payloads produced before
        # the page finishes loading are cached here and replayed exactly once.
        self._ui_lock = threading.Lock()
        self._window_ready = False
        self._pending_track = None
        self._pending_playback = None
        self._pending_lyrics = None
        self._pending_translations = None
        self._inflight_fetches = set()

        self.api = AppAPI(self)

    def get_hwnd(self):
        try:
            if self.window and hasattr(self.window, 'native') and self.window.native:
                handle = getattr(self.window.native, 'Handle', None)
                if handle is not None:
                    if hasattr(handle, 'ToInt64'):
                        return handle.ToInt64()
                    elif hasattr(handle, 'ToInt32'):
                        return handle.ToInt32()
                    elif isinstance(handle, int):
                        return handle
        except Exception:
            pass
        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, APP_TITLE)
            if hwnd:
                return hwnd
        except Exception:
            pass
        return None

    def start(self):
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        html_path = os.path.join(base_dir, "web", "index.html")

        # Native Media Listener
        self.media_listener = MediaListener(self.on_media_update)
        self.media_listener.start()

        # Global Hotkey Listener (Ctrl+Shift+G, M, H, L, Space)
        self.hotkey_thread = HotkeyThread(self)
        self.hotkey_thread.start()

        self.running = True

        settings = {}
        try:
            settings = get_cache().get_settings()
        except Exception as exc:
            logger.warning("Could not load persisted window settings: %s", exc)
        geometry = window_state.load_window_settings(settings)
        self.close_to_tray = geometry["close_to_tray"]
        self._mini_width = geometry.get("mini_width", window_state.DEFAULT_MINI_WIDTH)
        self._square_size = geometry.get("square_size", window_state.DEFAULT_SQUARE_SIZE)
        self._normal_geometry = {
            "x": geometry["x"],
            "y": geometry["y"],
            "width": geometry["width"],
            "height": geometry["height"],
        }

        window_kwargs = {}
        if geometry["x"] is not None and geometry["y"] is not None:
            window_kwargs["x"] = geometry["x"]
            window_kwargs["y"] = geometry["y"]
        if self.start_minimized:
            window_kwargs["hidden"] = True

        view_mode = geometry.get("view_mode", "card")
        is_startup_mini = view_mode == "mini"
        is_startup_square = view_mode == "square"
        self._is_mini = is_startup_mini
        self._is_square = is_startup_square

        if is_startup_mini:
            init_width = self._mini_width
            init_height = 270 if self._mini_expanded else MINI_HEIGHT
            init_min_w = window_state.MIN_MINI_WIDTH
            init_min_h = 85
        elif is_startup_square:
            init_width = self._square_size
            init_height = self._square_size
            init_min_w = window_state.MIN_SQUARE_SIZE
            init_min_h = window_state.MIN_SQUARE_SIZE
        else:
            init_width = geometry["width"]
            init_height = geometry["height"]
            init_min_w = window_state.MIN_WIDTH
            init_min_h = window_state.MIN_HEIGHT

        # Create pywebview window
        self.window = webview.create_window(
            title=APP_TITLE,
            url=html_path,
            js_api=self.api,
            width=init_width,
            height=init_height,
            min_size=(init_min_w, init_min_h),
            frameless=True,
            easy_drag=False,
            on_top=geometry["always_on_top"],
            transparent=False,
            **window_kwargs,
        )

        self._wire_window_events()
        self._start_tray(base_dir)

        if self.start_minimized and not self._tray_available:
            # Never leave the app invisible with no tray icon.
            logger.warning("Tray unavailable; showing the window instead of starting hidden")
            self._force_show_on_loaded = True

        webview.start(debug=False)

    def _wire_window_events(self):
        """Register replay, geometry and close-to-tray handlers."""
        if not self.window:
            return
        handlers = (
            ("loaded", self._on_window_loaded),
            ("closing", self._on_window_closing),
            ("moved", self._on_window_moved),
            ("resized", self._on_window_resized),
            ("shown", self._on_window_shown),
        )
        for event_name, handler in handlers:
            try:
                event = getattr(self.window.events, event_name)
                event += handler
            except Exception as exc:
                logger.warning(
                    "Could not register window %s handler: %s", event_name, exc
                )

    def _start_tray(self, base_dir):
        icon_path = os.path.join(base_dir, "icon.ico")
        try:
            self.tray = TrayIcon(
                self._on_tray_action,
                icon_path=icon_path,
                tooltip=TRAY_TOOLTIP,
            )
            self._tray_available = bool(self.tray.start())
        except Exception:
            logger.exception("Could not start the tray icon")
            self.tray = None
            self._tray_available = False

        if not self._tray_available:
            # Hiding without a tray icon would strand the app; fall back to a
            # normal close until the tray can be created.
            self.close_to_tray = False
            if self.tray:
                try:
                    self.tray.stop()
                except Exception:
                    logger.exception("Could not stop the failed tray icon")
                self.tray = None

    def _on_tray_action(self, action):
        try:
            if action == "quit":
                self.request_quit()
            elif action == "show_hide":
                self.toggle_show_hide()
            elif action == "play_pause":
                if self.media_listener:
                    self.media_listener.toggle_play_pause()
            elif action == "mini":
                self._show_window()
                self.evaluate_js(
                    "window.toggleMiniModeHotKey && window.toggleMiniModeHotKey()"
                )
            elif action == "square":
                self._show_window()
                self.evaluate_js(
                    "window.toggleSquareModeHotKey && window.toggleSquareModeHotKey()"
                )
            elif action == "settings":
                self._show_window()
                self.evaluate_js(
                    "window.openSettings && window.openSettings()"
                )
            else:
                logger.warning("Unknown tray action: %s", action)
        except Exception:
            logger.exception("Tray action %r failed", action)

    # ------------------------------------------------------------------
    # Window modes / geometry / close-to-tray
    # ------------------------------------------------------------------
    @property
    def is_fullscreen(self):
        return self._is_fullscreen

    @property
    def is_mini(self):
        return self._is_mini

    def _window_is_shown(self):
        try:
            if not self.window:
                return False
            return bool(self.window.events.shown.is_set())
        except Exception:
            return False

    def _on_window_shown(self, *args):
        try:
            if self._pending_mini and self._is_mini and self.window:
                self._pending_mini = False
                self._update_native_min_size(window_state.MIN_MINI_WIDTH, 50)
                curr_h = 270 if self._mini_expanded else MINI_HEIGHT
                self.window.resize(self._mini_width, curr_h)
            if self._pending_square and self._is_square and self.window:
                self._pending_square = False
                self._update_native_min_size(window_state.MIN_SQUARE_SIZE, window_state.MIN_SQUARE_SIZE)
                self.window.resize(self._square_size, self._square_size)
            if self._pending_fullscreen and self._is_fullscreen and self.window:
                self._pending_fullscreen = False
                self.window.toggle_fullscreen()
        except Exception:
            logger.exception("Could not apply the pending window mode")

    def _capture_normal_geometry(self):
        if self._is_mini or self._is_fullscreen or self._is_square:
            return
        geometry = self._geometry_snapshot()
        width, height = window_state.clamp_size(
            geometry.get("width"), geometry.get("height")
        )
        if width >= window_state.MIN_WIDTH and height >= window_state.MIN_HEIGHT:
            geometry["width"] = width
            geometry["height"] = height
            with self._geometry_lock:
                self._normal_geometry = geometry

    def _geometry_snapshot(self):
        with self._geometry_lock:
            geometry = dict(self._normal_geometry)
        if (
            self.window
            and not self._is_mini
            and not self._is_square
            and not self._is_fullscreen
            and self._window_is_shown()
        ):
            try:
                geometry.update(
                    {
                        "x": int(self.window.x),
                        "y": int(self.window.y),
                        "width": int(self.window.width),
                        "height": int(self.window.height),
                    }
                )
            except Exception as exc:
                logger.debug("Could not read the live window geometry: %s", exc)
        return geometry

    def _ignore_geometry_for(self, seconds=0.8):
        self._ignore_geometry_until = time.monotonic() + seconds

    def _geometry_events_allowed(self):
        return (
            not self._quitting
            and not self._is_mini
            and not self._is_square
            and not self._is_fullscreen
            and time.monotonic() >= self._ignore_geometry_until
        )

    def _on_window_moved(self, *args):
        if len(args) < 2 or not self._geometry_events_allowed():
            return
        try:
            x, y = int(args[0]), int(args[1])
        except (TypeError, ValueError):
            return
        with self._geometry_lock:
            self._normal_geometry["x"] = x
            self._normal_geometry["y"] = y
        self._schedule_geometry_save()

    def _on_window_resized(self, *args):
        if len(args) < 2 or not self._geometry_events_allowed():
            return
        try:
            width, height = int(args[0]), int(args[1])
        except (TypeError, ValueError):
            return
        if width <= 0 or height <= 0:
            return
        with self._geometry_lock:
            self._normal_geometry["width"] = width
            self._normal_geometry["height"] = height
        self._schedule_geometry_save()

    def _schedule_geometry_save(self):
        if self._quitting:
            return
        with self._geometry_lock:
            if self._geometry_timer is not None:
                self._geometry_timer.cancel()
            timer = threading.Timer(1.0, self._flush_geometry)
            timer.daemon = True
            self._geometry_timer = timer
            timer.start()

    def _flush_geometry(self):
        with self._geometry_lock:
            self._geometry_timer = None
        if not self._geometry_events_allowed():
            return
        self._save_window_state(include_view_mode=False)

    def _cancel_geometry_timer(self):
        with self._geometry_lock:
            timer = self._geometry_timer
            self._geometry_timer = None
        if timer is not None:
            timer.cancel()

    def _current_view_mode(self):
        if getattr(self, "_is_fullscreen", False):
            return "fullscreen"
        if getattr(self, "_is_mini", False):
            return "mini"
        if getattr(self, "_is_square", False):
            return "square"
        return "card"

    def _persist_owned(self, values):
        try:
            return window_state.persist_settings(values)
        except Exception as exc:
            logger.warning("Could not persist settings %r: %s", values, exc)
            return False

    def _save_window_state(self, include_view_mode=True):
        geometry = self._geometry_snapshot()
        values = {}
        is_mini = getattr(self, "_is_mini", False)
        is_square = getattr(self, "_is_square", False)
        is_fullscreen = getattr(self, "_is_fullscreen", False)

        if is_mini:
            values["mini_width"] = window_state.clamp_mini_width(geometry.get("width"))
        elif is_square:
            values["square_size"] = window_state.clamp_square_size(geometry.get("width"))
        elif not is_fullscreen:
            width, height = window_state.clamp_size(
                geometry.get("width"), geometry.get("height")
            )
            values["window_width"] = width
            values["window_height"] = height
            x = geometry.get("x")
            y = geometry.get("y")
            if x is not None and y is not None:
                x, y = window_state.clamp_position(x, y, width, height)
                values["window_x"] = x
                values["window_y"] = y
            with self._geometry_lock:
                self._normal_geometry.update(
                    {"x": x, "y": y, "width": width, "height": height}
                )
        if include_view_mode:
            values["view_mode"] = self._current_view_mode()
            # Do not persist the in-memory fallback used when the tray failed.
            if self._tray_available:
                values["close_to_tray"] = self.close_to_tray
        self._persist_owned(values)

    def _update_native_min_size(self, min_w, min_h):
        try:
            if not self.window:
                return
            self.window.min_size = (int(min_w), int(min_h))
            native = getattr(self.window, "native", None)
            if not native:
                return
            from System.Drawing import Size
            scale = getattr(native, "_scale", 1.0)
            target_size = Size(int(min_w * scale), int(min_h * scale))

            if getattr(native, "InvokeRequired", False):
                from System import Action
                native.Invoke(Action(lambda: setattr(native, "MinimumSize", target_size)))
            else:
                native.MinimumSize = target_size
        except Exception as exc:
            logger.debug("Could not update native MinimumSize: %s", exc)

    def set_mini_mode(self, enabled):
        enabled = bool(enabled)
        if enabled == self._is_mini:
            return
        self._capture_normal_geometry()
        if enabled and self._is_fullscreen:
            self._is_fullscreen = False
            self._pending_fullscreen = False
            try:
                if self.window and self._window_is_shown():
                    self.window.toggle_fullscreen()
            except Exception as exc:
                logger.warning("Could not leave fullscreen for mini mode: %s", exc)

        self._is_mini = enabled
        self._ignore_geometry_for()
        if enabled:
            if self._is_square:
                self._is_square = False
                self._pending_square = False
            self._update_native_min_size(window_state.MIN_MINI_WIDTH, 50)
            if self.window and self._window_is_shown():
                try:
                    curr_h = 270 if self._mini_expanded else MINI_HEIGHT
                    self.window.resize(self._mini_width, curr_h)
                except Exception as exc:
                    logger.warning("Could not resize into mini mode: %s", exc)
            else:
                self._pending_mini = True
        else:
            self._pending_mini = False
            self._update_native_min_size(window_state.MIN_WIDTH, window_state.MIN_HEIGHT)
            geometry = dict(self._normal_geometry)
            width, height = window_state.clamp_size(
                geometry.get("width"), geometry.get("height")
            )
            geometry["width"] = width
            geometry["height"] = height
            with self._geometry_lock:
                self._normal_geometry["width"] = width
                self._normal_geometry["height"] = height
            if self.window and self._window_is_shown():
                try:
                    x, y = geometry.get("x"), geometry.get("y")
                    if x is not None and y is not None:
                        self.window.move(int(x), int(y))
                    self.window.resize(width, height)
                except Exception as exc:
                    logger.warning("Could not restore the normal window size: %s", exc)

        self._persist_owned(
            {"view_mode": "mini" if enabled else "card"}
        )

    def set_mini_expand(self, is_expanded):
        self._mini_expanded = bool(is_expanded)
        if self.window and self._is_mini and self._window_is_shown():
            try:
                curr_h = 270 if is_expanded else MINI_HEIGHT
                self.window.resize(self._mini_width, curr_h)
            except Exception as exc:
                logger.warning("Could not toggle mini expand: %s", exc)

    def set_mini_width(self, width):
        clamped = window_state.clamp_mini_width(width)
        self._mini_width = clamped
        if self.window and self._is_mini and self._window_is_shown():
            try:
                curr_h = 270 if self._mini_expanded else MINI_HEIGHT
                self.window.resize(clamped, curr_h)
            except Exception as exc:
                logger.warning("Could not resize mini window width: %s", exc)
        self._persist_owned({"mini_width": clamped})
        return clamped

    def set_square_mode(self, enabled):
        enabled = bool(enabled)
        if enabled == self._is_square:
            return
        if not self._is_mini:
            self._capture_normal_geometry()
        if enabled and self._is_fullscreen:
            self._is_fullscreen = False
            self._pending_fullscreen = False
            try:
                if self.window and self._window_is_shown():
                    self.window.toggle_fullscreen()
            except Exception as exc:
                logger.warning("Could not leave fullscreen for square mode: %s", exc)
        if enabled and self._is_mini:
            self._is_mini = False
            self._pending_mini = False

        self._is_square = enabled
        self._ignore_geometry_for()
        if enabled:
            self._update_native_min_size(window_state.MIN_SQUARE_SIZE, window_state.MIN_SQUARE_SIZE)
            if self.window and self._window_is_shown():
                try:
                    self.window.resize(self._square_size, self._square_size)
                except Exception as exc:
                    logger.warning("Could not resize into square mode: %s", exc)
            else:
                self._pending_square = True
        else:
            self._pending_square = False
            self._update_native_min_size(window_state.MIN_WIDTH, window_state.MIN_HEIGHT)
            geometry = dict(self._normal_geometry)
            width, height = window_state.clamp_size(
                geometry.get("width"), geometry.get("height")
            )
            geometry["width"] = width
            geometry["height"] = height
            with self._geometry_lock:
                self._normal_geometry["width"] = width
                self._normal_geometry["height"] = height
            if self.window and self._window_is_shown():
                try:
                    x, y = geometry.get("x"), geometry.get("y")
                    if x is not None and y is not None:
                        self.window.move(int(x), int(y))
                    self.window.resize(width, height)
                except Exception as exc:
                    logger.warning("Could not restore normal window size: %s", exc)

        self._persist_owned(
            {"view_mode": "square" if enabled else "card"}
        )

    def set_square_size(self, size):
        clamped = window_state.clamp_square_size(size)
        self._square_size = clamped
        if self.window and self._is_square and self._window_is_shown():
            try:
                self.window.resize(clamped, clamped)
            except Exception as exc:
                logger.warning("Could not resize square window: %s", exc)
        self._persist_owned({"square_size": clamped})
        return clamped

    def set_fullscreen_mode(self, enabled):
        enabled = bool(enabled)
        if enabled == self._is_fullscreen:
            return
        if enabled:
            if self._is_mini:
                self._is_mini = False
                self._pending_mini = False
            elif self._is_square:
                self._is_square = False
                self._pending_square = False
            else:
                self._capture_normal_geometry()
        self._is_fullscreen = enabled
        self._ignore_geometry_for()
        if self.window and self._window_is_shown():
            try:
                self.window.toggle_fullscreen()
            except Exception as exc:
                logger.warning("Could not toggle fullscreen: %s", exc)
        else:
            self._pending_fullscreen = enabled

        if not enabled and self.window and self._window_is_shown() and not self._is_mini:
            try:
                width, height = window_state.clamp_size(
                    self._normal_geometry.get("width"),
                    self._normal_geometry.get("height"),
                )
                self.window.resize(width, height)
            except Exception as exc:
                logger.warning("Could not restore window size after fullscreen: %s", exc)

        if enabled:
            view_mode = "fullscreen"
        elif self._is_mini:
            view_mode = "mini"
        else:
            view_mode = "card"
        self._persist_owned({"view_mode": view_mode})

    def set_close_to_tray(self, enabled):
        enabled = bool(enabled)
        if enabled and not self._tray_available:
            logger.warning("Cannot enable close-to-tray without a tray icon")
            return False
        self.close_to_tray = enabled
        self._persist_owned({"close_to_tray": enabled})
        return True

    def set_start_with_windows(self, enabled):
        enabled = bool(enabled)
        try:
            changed = startup.set_start_with_windows(enabled)
        except Exception as exc:
            logger.warning("Could not change start-with-Windows: %s", exc)
            changed = False
        if changed:
            self._persist_owned({"start_with_windows": enabled})
        return changed

    def hide_to_tray(self):
        if not self.window:
            return False
        self._cancel_geometry_timer()
        self._save_window_state()
        try:
            self.window.hide()
            return True
        except Exception as exc:
            logger.warning("Could not hide the window to the tray: %s", exc)
            return False

    def _on_window_closing(self, *args):
        if self._quitting:
            return True
        try:
            self._cancel_geometry_timer()
            self._save_window_state()
            if not self.close_to_tray or not self._tray_available:
                return True
            self.window.hide()
            return False
        except Exception:
            logger.exception("Close-to-tray handler failed")
            # Do not leave a window that cannot be closed.
            return True

    def _show_window(self):
        try:
            hwnd = self.get_hwnd()
            if not hwnd:
                return False
            user32.ShowWindow(ctypes.c_void_p(hwnd), 9)  # SW_RESTORE
            user32.SetForegroundWindow(ctypes.c_void_p(hwnd))
            return True
        except Exception as exc:
            logger.warning("Could not show the window: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    def request_quit(self):
        with self._quit_lock:
            if self._quit_done or self._quit_running or self._quit_requested:
                return
            self._quit_requested = True
        threading.Thread(
            target=self.quit, name="SpotifyLyricsQuit", daemon=True
        ).start()

    def quit(self):
        """Stop listeners, save state, destroy the window and release the mutex."""
        with self._quit_lock:
            if self._quit_done:
                return
            if self._quit_running:
                return
            self._quit_running = True
            self._quitting = True

        try:
            self._cancel_geometry_timer()
            try:
                self._save_window_state()
            except Exception:
                logger.exception("Could not save window state while quitting")
            try:
                self.stop()
            except Exception:
                logger.exception("Could not stop background services")
            if self.window:
                try:
                    self.window.destroy()
                except Exception as exc:
                    logger.warning("Could not destroy the window: %s", exc)
        finally:
            if self.tray:
                try:
                    self.tray.stop()
                except Exception:
                    logger.exception("Could not stop the tray icon")
                self.tray = None
            with self._quit_lock:
                self._quit_running = False
                self._quit_done = True
            self._quit_finished.set()
            if self.single_instance:
                self.single_instance.release()

    def shutdown(self, timeout=10.0):
        self.quit()
        if not self._quit_finished.is_set():
            self._quit_finished.wait(timeout)

    def on_global_hotkey(self, hotkey_id):
        """Handles Windows global keyboard shortcuts."""
        try:
            if hotkey_id == 1:  # Ctrl+Shift+G: Ghost Mode
                self.evaluate_js("window.toggleGhostModeHotKey && window.toggleGhostModeHotKey()")
            elif hotkey_id == 2:  # Ctrl+Shift+M: Mini Island
                self.evaluate_js("window.toggleMiniModeHotKey && window.toggleMiniModeHotKey()")
            elif hotkey_id == 3:  # Ctrl+Shift+H: Boss Key (Hide / Show)
                self.toggle_show_hide()
            elif hotkey_id == 4:  # Ctrl+Shift+L: Cycle View Mode
                self.evaluate_js("window.cycleViewMode && window.cycleViewMode()")
            elif hotkey_id == 5:  # Ctrl+Shift+Space: Play / Pause Spotify
                if self.media_listener:
                    self.media_listener.toggle_play_pause()
            elif hotkey_id == 6:  # Ctrl+Shift+S: Square Mode
                self.evaluate_js("window.toggleSquareModeHotKey && window.toggleSquareModeHotKey()")
        except Exception as e:
            print("Hotkey handler error:", e)

    def toggle_show_hide(self):
        try:
            hwnd = self.get_hwnd()
            if hwnd:
                SW_HIDE = 0
                SW_RESTORE = 9
                is_visible = user32.IsWindowVisible(ctypes.c_void_p(hwnd))
                if is_visible:
                    user32.ShowWindow(ctypes.c_void_p(hwnd), SW_HIDE)
                else:
                    user32.ShowWindow(ctypes.c_void_p(hwnd), SW_RESTORE)
                    user32.SetForegroundWindow(ctypes.c_void_p(hwnd))
        except Exception as e:
            print("Toggle show/hide error:", e)

    @staticmethod
    def _position_seconds(data):
        if data.get("position_ms") is not None:
            try:
                return max(0.0, float(data["position_ms"]) / 1000.0)
            except (TypeError, ValueError):
                pass
        try:
            return max(0.0, float(data.get("position", 0.0) or 0.0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _playback_rate(data):
        try:
            rate = float(data.get("playback_rate", 1.0))
        except (TypeError, ValueError):
            return 1.0
        if not math.isfinite(rate) or rate <= 0:
            return 1.0
        return max(0.25, min(4.0, rate))

    def _is_current_fetch(self, generation_id, artist, title):
        """True only while this generation still owns the active lyrics target."""
        with self.state_lock:
            return (
                generation_id == self.current_generation_id
                and self.current_lyrics_key == _make_track_key(artist, title)
            )

    def _update_discord(self, artist, title, status, position_seconds):
        if title and artist and status == 4:
            self.discord_rpc.update_presence(title, artist, "", position_seconds)
        elif status == 5:
            self.discord_rpc.clear()

    # ------------------------------------------------------------------
    # Window-ready payload delivery / replay
    # ------------------------------------------------------------------
    def _deliver_track(self, generation_id, payload):
        with self._ui_lock:
            with self.state_lock:
                if generation_id != self.current_generation_id:
                    return
                self._pending_track = (generation_id, payload)
                ready = self._window_ready
            if ready:
                self.evaluate_js(f"window.updateTrack({json.dumps(payload)})")

    def _deliver_playback(self, generation_id, payload, send=True):
        with self._ui_lock:
            with self.state_lock:
                if generation_id != self.current_generation_id:
                    return
                self._pending_playback = (generation_id, payload)
                ready = self._window_ready and send
            if ready:
                self.evaluate_js(
                    f"window.updatePlaybackState({json.dumps(payload)})"
                )

    def _deliver_lyrics(self, generation_id, payload):
        with self._ui_lock:
            with self.state_lock:
                if generation_id != self.current_generation_id:
                    return
                self._pending_lyrics = (generation_id, payload)
                ready = self._window_ready
            if not ready:
                return
            if payload is None:
                self.evaluate_js("window.updateLyrics(null)")
            else:
                self.evaluate_js(f"window.updateLyrics({json.dumps(payload)})")

    def _deliver_translations(self, generation_id, payload):
        with self._ui_lock:
            with self.state_lock:
                if generation_id != self.current_generation_id:
                    return
                self._pending_translations = (generation_id, payload)
                ready = self._window_ready
            if ready:
                self.evaluate_js(
                    f"window.updateTranslations({json.dumps(payload)})"
                )

    def _on_window_loaded(self, *args):
        """Replay the latest payloads once, after the webview can execute JS."""
        with self._ui_lock:
            with self.state_lock:
                if self._window_ready:
                    return
                self._window_ready = True
                generation_id = self.current_generation_id
                track = self._pending_track
                playback = self._pending_playback
                lyrics = self._pending_lyrics
                translations = self._pending_translations
                artist = self.current_artist
                title = self.current_title
                duration = self.current_duration
                lyrics_target = self.current_lyrics_key
                inflight = generation_id in self._inflight_fetches

            def current(entry):
                return entry is not None and entry[0] == generation_id

            if current(track):
                self.evaluate_js(
                    f"window.updateTrack({json.dumps(track[1])})"
                )
            if current(playback):
                self.evaluate_js(
                    f"window.updatePlaybackState({json.dumps(playback[1])})"
                )
            if current(lyrics):
                if lyrics[1] is None:
                    self.evaluate_js("window.updateLyrics(null)")
                else:
                    self.evaluate_js(
                        f"window.updateLyrics({json.dumps(lyrics[1])})"
                    )
            if current(translations):
                self.evaluate_js(
                    f"window.updateTranslations({json.dumps(translations[1])})"
                )

            startup_mode = self._current_view_mode()
            if startup_mode in ("square", "mini", "fullscreen"):
                self.evaluate_js(
                    f"window.applyWindowMode && window.applyWindowMode({json.dumps(startup_mode)}, {{backend: false}})"
                )

            has_lyrics = (
                current(lyrics)
                and isinstance(lyrics[1], dict)
                and bool(lyrics[1].get("lines"))
            )
            live_key = _make_track_key(artist, title)
            need_fetch = bool(
                artist
                and title
                and not has_lyrics
                and not inflight
                and lyrics_target == live_key
            )

        if need_fetch:
            threading.Thread(
                target=self._fetch_and_translate_lyrics,
                args=(artist, title, duration, generation_id),
                daemon=True,
            ).start()

        if getattr(self, "_force_show_on_loaded", False):
            self._force_show_on_loaded = False
            try:
                if self.window:
                    self.window.show()
            except Exception as exc:
                logger.warning("Could not show the window after load: %s", exc)

    def on_media_update(self, data):
        if not data:
            return

        track_changed = bool(data.get("track_changed", False))
        try:
            status = int(data.get("status", 0))
        except (TypeError, ValueError):
            status = 0
        position = self._position_seconds(data)

        with self.state_lock:
            current_track = self.current_track
            current_artist = self.current_artist
            current_title = self.current_title

        # Delta ticks omit title/artist; fall back to the remembered track.
        title = data.get("title")
        artist = data.get("artist")
        title = current_title if title is None else title
        artist = current_artist if artist is None else artist
        title = title or ""
        artist = artist or ""
        track_key = _make_track_key(artist, title)

        if track_changed or not current_track or track_key != current_track:
            self._apply_track_change(data, artist, title, status, position)
        else:
            self._apply_playback_delta(data, status, position)

        # Discord RPC already throttles internally; keep it on both paths.
        self._update_discord(artist, title, status, position)

    def _apply_track_change(self, data, artist, title, status, position):
        album = data.get("album", "")
        duration = data.get("duration")
        if duration is None and data.get("duration_ms") is not None:
            try:
                duration = float(data["duration_ms"]) / 1000.0
            except (TypeError, ValueError):
                duration = 0.0
        try:
            duration = float(duration or 0.0)
        except (TypeError, ValueError):
            duration = 0.0
        track_key = _make_track_key(artist, title)

        with self.state_lock:
            self.current_generation_id += 1
            generation_id = self.current_generation_id
            self.current_track = track_key
            self.current_artist = artist
            self.current_title = title
            self.current_duration = duration
            self.current_lyrics_key = track_key
            self._pending_lyrics = None
            self._pending_translations = None
            self.last_position = position
            self.last_sync_time = time.time()
            self.playback_status = status

        # History and favourite state are read once per track, never per tick.
        if title and artist:
            self.lyrics_service.cache.record_song_play(
                artist, title, album, data.get("thumbnail", "")
            )
            is_favorite = self.lyrics_service.cache.is_favorite(artist, title)
        else:
            is_favorite = False

        payload = dict(data)
        payload["is_favorite"] = is_favorite
        payload["track_changed"] = True
        payload.setdefault("status", status)
        payload.setdefault("position", position)
        payload.setdefault("duration", duration)
        payload.setdefault("playback_rate", self._playback_rate(data))
        payload.setdefault("is_playing", status == 4)

        playback_payload = {
            "position_ms": int(round(position * 1000)),
            "is_playing": status == 4,
            "playback_rate": self._playback_rate(data),
            "duration_ms": int(round(duration * 1000)),
        }
        self._deliver_track(generation_id, payload)
        # Stored for the loaded replay, but not sent separately while the full
        # track payload already carries the position/status.
        self._deliver_playback(generation_id, playback_payload, send=False)

        if title and artist:
            threading.Thread(
                target=self._fetch_and_translate_lyrics,
                args=(artist, title, duration, generation_id),
                daemon=True
            ).start()

    def _apply_playback_delta(self, data, status, position):
        with self.state_lock:
            generation_id = self.current_generation_id
            self.last_position = position
            self.last_sync_time = time.time()
            self.playback_status = status
            duration = self.current_duration

        if data.get("duration") is not None:
            try:
                duration = float(data.get("duration") or 0.0)
            except (TypeError, ValueError):
                pass
        elif data.get("duration_ms") is not None:
            try:
                duration = float(data["duration_ms"]) / 1000.0
            except (TypeError, ValueError):
                pass

        with self.state_lock:
            self.current_duration = duration

        payload = {
            "position_ms": int(round(position * 1000)),
            "is_playing": status == 4,
            "playback_rate": self._playback_rate(data),
            "duration_ms": int(round(duration * 1000)),
        }
        self._deliver_playback(generation_id, payload)

    def load_history_lyrics(self, artist, title):
        """Fetch a history song without disturbing the live track identity."""
        with self.state_lock:
            self.current_generation_id += 1
            generation_id = self.current_generation_id
            self.current_lyrics_key = _make_track_key(artist, title)
            self._pending_lyrics = None
            self._pending_translations = None
        threading.Thread(
            target=self._fetch_and_translate_lyrics,
            args=(artist, title, 0, generation_id),
            daemon=True
        ).start()

    def _fetch_and_translate_lyrics(self, artist, title, duration, generation_id=None,
                                    candidate=None):
        with self.state_lock:
            if generation_id is None:
                generation_id = self.current_generation_id
            if self.current_lyrics_key is None:
                self.current_lyrics_key = _make_track_key(artist, title)
            if generation_id in self._inflight_fetches:
                return
            self._inflight_fetches.add(generation_id)
            preview = _make_track_key(artist, title) != _make_track_key(
                self.current_artist, self.current_title
            )

        def should_abort():
            return not self._is_current_fetch(generation_id, artist, title)

        try:
            if should_abort():
                return

            # 1. Fetch Synced Lyrics
            lyrics_data = self.lyrics_service.fetch_lyrics(
                artist, title, duration, should_abort=should_abort,
                candidate=candidate
            )
            if should_abort():
                return
            if not lyrics_data or not lyrics_data.get("lines"):
                self._deliver_lyrics(generation_id, None)
                return

            raw_lines = lyrics_data["lines"]
            provider_name = lyrics_data.get("provider") or "lrclib"

            # 2. INSTANT DISPLAY
            initial_payload = {
                "title": lyrics_data.get("title"),
                "artist": lyrics_data.get("artist"),
                "provider": provider_name,
                "id": lyrics_data.get("id"),
                "preview": preview,
                "is_synced": bool(lyrics_data.get("is_synced", False)),
                "lang": "unknown",
                "lines": raw_lines
            }
            if should_abort():
                return
            self._deliver_lyrics(generation_id, initial_payload)

            # 3. BACKGROUND TRANSLATION & PHONETICS
            translated_lines, dominant_lang = self.translator_service.translate_lines(
                raw_lines, should_abort=should_abort
            )
            if should_abort():
                return

            # 4. Stream translations + romanizations into rendered lines
            trans_payload = {
                "lang": dominant_lang,
                "provider": provider_name,
                "lines": translated_lines
            }
            if should_abort():
                return
            self._deliver_translations(generation_id, trans_payload)

        except Exception as e:
            logger.warning("Lyrics/Translation error: %s", e)
            if not should_abort():
                self._deliver_lyrics(generation_id, None)
        finally:
            with self.state_lock:
                self._inflight_fetches.discard(generation_id)

    def reload_current_lyrics(self):
        with self.state_lock:
            artist = self.current_artist
            title = self.current_title
            duration = self.current_duration
            if not artist or not title:
                return
            # Bumping the generation invalidates any in-flight language switch
            # or lyrics fetch for the previous generation.
            self.current_generation_id += 1
            generation_id = self.current_generation_id
            self.current_lyrics_key = _make_track_key(artist, title)
            self._pending_lyrics = None
            self._pending_translations = None

        threading.Thread(
            target=self._fetch_and_translate_lyrics,
            args=(artist, title, duration, generation_id),
            daemon=True
        ).start()

    def evaluate_js(self, script):
        if self.window:
            try:
                self.window.evaluate_js(script)
            except Exception:
                pass

    def stop(self):
        self.running = False
        if self.hotkey_thread:
            self.hotkey_thread.stop()
        if self.media_listener:
            self.media_listener.stop()
        if self.discord_rpc:
            self.discord_rpc.close()


# Brand alias
LyriqApp = SpotifyLyricsApp


def _configure_logging():
    if logging.getLogger().handlers:
        return
    handlers = [logging.StreamHandler()]
    try:
        log_path = app_paths.get_logs_dir() / "app.log"
        handlers.insert(
            0, logging.FileHandler(log_path, encoding="utf-8")
        )
    except OSError as exc:
        logger.warning("Could not open the log file: %s", exc)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main(argv=None):
    _configure_logging()
    args = list(sys.argv[1:] if argv is None else argv)
    start_minimized = "--minimized" in args

    instance = SingleInstance(window_title=APP_TITLE)
    if not instance.acquire():
        logger.info("Lyriq is already running; exiting")
        return 0

    app = SpotifyLyricsApp(start_minimized=start_minimized)
    app.single_instance = instance
    try:
        app.start()
    except Exception:
        logger.exception("Fatal Lyriq startup error")
        return 1
    finally:
        try:
            app.shutdown()
        finally:
            instance.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
