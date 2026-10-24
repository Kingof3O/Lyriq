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

logger = logging.getLogger("SpotifyLyrics")

APP_TITLE = "Spotify Lyrics & Translation"
TRAY_TOOLTIP = "Spotify Lyrics"
MINI_WIDTH = 560
MINI_HEIGHT = 95


def _make_track_key(artist, title):
    return f"{artist or ''} - {title or ''}"


class HotkeyThread(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self.running = True
        self.thread_id = None

    def run(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self.thread_id = kernel32.GetCurrentThreadId()

        MOD_CONTROL = 0x0002
        MOD_SHIFT = 0x0004
        MOD_NOREPEAT = 0x4000

        # Global Hotkeys:
        # ID 1: Ctrl + Shift + G -> Ghost mode (click-through toggle)
        # ID 2: Ctrl + Shift + M -> Mini Island mode toggle
        # ID 3: Ctrl + Shift + H -> Boss Key (Hide / Show)
        # ID 4: Ctrl + Shift + L -> Lyrics View Mode (Dual / Trans / Orig)
        # ID 5: Ctrl + Shift + Space -> Spotify Play / Pause
        user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x47)  # 'G'
        user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x4D)  # 'M'
        user32.RegisterHotKey(None, 3, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x48)  # 'H'
        user32.RegisterHotKey(None, 4, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x4C)  # 'L'
        user32.RegisterHotKey(None, 5, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x20)  # VK_SPACE

        msg = ctypes.wintypes.MSG()
        while self.running:
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:
                break
            if msg.message == 0x0312:  # WM_HOTKEY
                hotkey_id = msg.wParam
                self.app.on_global_hotkey(hotkey_id)
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        for hid in range(1, 6):
            try:
                user32.UnregisterHotKey(None, hid)
            except Exception:
                pass

    def stop(self):
        self.running = False
        if self.thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass


user32 = ctypes.windll.user32
try:
    user32.SetWindowPos.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint
    ]
    user32.SetWindowPos.restype = ctypes.c_int
except Exception:
    pass

class AppAPI:
    def __init__(self, app):
        self._app = app
        self._sleep_timer = None

    def toggle_pin(self, is_pinned):
        self._app._persist_owned({"always_on_top": bool(is_pinned)})
        try:
            hwnd = self._app.get_hwnd()
            if hwnd:
                HWND_TOPMOST = ctypes.c_void_p(-1)
                HWND_NOTOPMOST = ctypes.c_void_p(-2)
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOACTIVATE = 0x0010
                h_after = HWND_TOPMOST if is_pinned else HWND_NOTOPMOST
                user32.SetWindowPos(
                    ctypes.c_void_p(hwnd),
                    h_after,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                )
        except Exception as e:
            print("Toggle pin error:", e)

    def toggle_fullscreen(self):
        self._app.set_fullscreen_mode(not self._app.is_fullscreen)

    def toggle_mini_mode(self, is_mini):
        self._app.set_mini_mode(bool(is_mini))

    def toggle_mini_expand(self, is_expanded):
        if self._app.window:
            if is_expanded:
                self._app.window.resize(MINI_WIDTH, 270)
            else:
                self._app.window.resize(MINI_WIDTH, MINI_HEIGHT)

    def set_close_to_tray(self, enabled):
        """Enables or disables hiding the window instead of closing it."""
        return self._app.set_close_to_tray(bool(enabled))

    def set_start_with_windows(self, enabled):
        """Adds or removes the per-user Run registry entry."""
        return self._app.set_start_with_windows(bool(enabled))

    def get_startup_state(self):
        """Returns the live registry state for the startup toggle."""
        try:
            enabled = startup.is_start_with_windows()
        except Exception as exc:
            logger.warning("Could not read startup state: %s", exc)
            enabled = False
        return {"enabled": enabled, "supported": True}

    def toggle_ghost_mode(self, is_ghost):
        """Click-through mode for gaming: clicks pass through to the game beneath!"""
        try:
            hwnd = self._app.get_hwnd()
            if hwnd:
                GWL_EXSTYLE = -20
                WS_EX_TRANSPARENT = 0x00000020
                WS_EX_LAYERED = 0x00080000
                style = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE)
                if is_ghost:
                    user32.SetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
                else:
                    user32.SetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT)
        except Exception as e:
            print("Ghost mode toggle error:", e)

    def adjust_volume(self, delta):
        """Adjusts Windows master volume via native keybd_event (delta > 0: up, delta < 0: down)."""
        try:
            user32 = ctypes.windll.user32
            VK_VOLUME_UP = 0xAF
            VK_VOLUME_DOWN = 0xAE
            vk = VK_VOLUME_UP if delta > 0 else VK_VOLUME_DOWN
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
        except Exception as e:
            print("Volume adjust error:", e)

    def set_target_language(self, lang):
        """Switches the target translation language dynamically (e.g. 'es', 'fr', 'ar', 'de')."""
        self._app.translator_service.set_target_lang(lang)
        self._app.reload_current_lyrics()

    def set_sleep_timer(self, minutes):
        """Auto-pause Spotify after specified minutes."""
        if self._sleep_timer:
            self._sleep_timer.cancel()
            self._sleep_timer = None

        minutes = float(minutes)
        if minutes > 0:
            def trigger_pause():
                if self._app.media_listener:
                    self._app.media_listener.toggle_play_pause()
                self._app.evaluate_js("window.onSleepTimerTriggered()")

            self._sleep_timer = threading.Timer(minutes * 60, trigger_pause)
            self._sleep_timer.daemon = True
            self._sleep_timer.start()

    def export_lyrics(self, lrc_content, filename):
        """Exports synchronized bilingual lyrics to Desktop as .lrc."""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            safe_name = "".join(c for c in filename if c.isalnum() or c in " ._-").strip() or "lyrics.lrc"
            if not safe_name.endswith(".lrc"):
                safe_name += ".lrc"
            out_path = os.path.join(desktop, safe_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(lrc_content)
            return f"Exported to Desktop: {safe_name}"
        except Exception as e:
            return f"Export error: {e}"

    def export_srt(self, srt_content, filename):
        """Exports synchronized bilingual subtitles to Desktop as .srt."""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            safe_name = "".join(c for c in filename if c.isalnum() or c in " ._-").strip() or "lyrics.srt"
            if not safe_name.endswith(".srt"):
                safe_name += ".srt"
            out_path = os.path.join(desktop, safe_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            return f"Exported Subtitles to Desktop: {safe_name}"
        except Exception as e:
            return f"Export error: {e}"

    def export_lyric_sheet(self, html_content, filename):
        """Exports poster-style printable HTML lyric sheet to Desktop."""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            safe_name = "".join(c for c in filename if c.isalnum() or c in " ._-").strip() or "Lyric_Sheet.html"
            if not safe_name.endswith(".html"):
                safe_name += ".html"
            out_path = os.path.join(desktop, safe_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return f"Exported Printable Sheet to Desktop: {safe_name}"
        except Exception as e:
            return f"Export error: {e}"

    def lookup_word(self, word):
        """Instant translation & dictionary lookup for a single word/phrase."""
        try:
            word = word.strip()
            if not word:
                return {"word": "", "trans": "", "romaji": "", "lang": "unknown"}

            romaji = Romanizer.romanize(word)
            target = self._app.translator_service.target_lang or "en"

            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target,
                "dt": ["t", "rm"],
                "q": word
            }
            url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params, doseq=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                trans_parts = []
                api_romaji = ""
                if data and len(data) > 0 and isinstance(data[0], list):
                    for seg in data[0]:
                        if seg and seg[0] and isinstance(seg[0], str):
                            trans_parts.append(seg[0])
                        elif seg and seg[0] is None and len(seg) > 3 and isinstance(seg[3], str):
                            api_romaji = seg[3]

                trans = "".join(trans_parts).strip()
                lang = data[2] if len(data) > 2 and isinstance(data[2], str) else "unknown"

                return {
                    "word": word,
                    "trans": trans,
                    "romaji": api_romaji or romaji,
                    "lang": lang
                }
        except Exception as e:
            return {"word": word, "trans": f"Lookup error: {e}", "romaji": "", "lang": "unknown"}

    # Settings, per-song offsets & cache management
    def get_settings(self):
        """Returns every persisted setting (JSON-decoded by the cache)."""
        return get_cache().get_settings()

    def save_settings(self, values):
        """Persists a mapping of settings. Unknown keys are kept as-is."""
        if not isinstance(values, dict):
            return False
        return get_cache().set_settings(values)

    def get_song_offset(self, artist, title):
        """Returns the saved lyric offset in seconds for a track."""
        return get_cache().get_song_offset(artist, title)

    def set_song_offset(self, artist, title, offset):
        """Saves the lyric offset in seconds for a track and returns it."""
        return get_cache().set_song_offset(artist, title, offset)

    def clear_cache(self):
        """Clears lyrics/translation/thumbnail caches, keeping user data."""
        return get_cache().clear_cache()

    def get_cache_stats(self):
        """Returns data directory, database size and cache row counts."""
        return get_cache().get_cache_stats()

    # Song History & Favorites
    def toggle_favorite(self, artist, title):
        return self._app.lyrics_service.cache.toggle_favorite(artist, title)

    def get_song_history(self):
        return self._app.lyrics_service.cache.get_song_history()

    def load_history_song(self, artist, title):
        if artist and title:
            self._app.load_history_lyrics(artist, title)

    # Vocabulary Notebook
    def save_vocab_word(self, word, romaji, meaning, lang, song_title):
        return self._app.lyrics_service.cache.save_vocab_word(word, romaji, meaning, lang, song_title)

    def get_vocab_words(self):
        return self._app.lyrics_service.cache.get_vocab_words()

    def delete_vocab_word(self, word_id):
        self._app.lyrics_service.cache.delete_vocab_word(int(word_id))

    def export_vocab_csv(self):
        try:
            words = self._app.lyrics_service.cache.get_vocab_words()
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            out_path = os.path.join(desktop, "Spotify_Vocabulary_Deck.csv")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("Word\tPhonetics\tMeaning\tLanguage\tSong\n")
                for w in words:
                    f.write(f"{w['word']}\t{w['romaji']}\t{w['meaning']}\t{w['lang']}\t{w['song_title']}\n")
            return f"Exported {len(words)} words to Desktop (Spotify_Vocabulary_Deck.csv)"
        except Exception as e:
            return f"Export error: {e}"

    def toggle_discord_rpc(self, enabled):
        self._app.discord_rpc.enabled = bool(enabled)
        if not enabled:
            self._app.discord_rpc.clear()

    def seek(self, seconds):
        if self._app.media_listener:
            self._app.media_listener.seek(float(seconds))

    def play_pause(self):
        if self._app.media_listener:
            self._app.media_listener.toggle_play_pause()

    def next_track(self):
        if self._app.media_listener:
            self._app.media_listener.next_track()

    def prev_track(self):
        if self._app.media_listener:
            self._app.media_listener.prev_track()

    def minimize(self):
        if self._app.window:
            self._app.window.minimize()

    def close(self):
        """Closes to the tray when enabled, otherwise shuts the app down."""
        if self._app.close_to_tray:
            self._app.hide_to_tray()
            return True
        self._app.request_quit()
        return True

    def quit(self):
        """Fully exits the app; safe to call from the tray or JS."""
        self._app.request_quit()
        return True

    def retry_lyrics(self):
        self._app.reload_current_lyrics()

    # ------------------------------------------------------------------
    # Lyrics provider / manual selection APIs
    # ------------------------------------------------------------------
    def search_lyrics(self, artist, title, duration=0):
        """Returns scored lyric candidates for the current track."""
        try:
            return self._app.lyrics_service.search_lyrics(
                artist or "", title or "", duration or 0
            )
        except Exception as exc:
            logger.warning("Lyrics search failed: %s", exc)
            return []

    def select_lyrics(self, artist, title, duration, candidate):
        """Fetches an explicitly chosen candidate for the lyrics pane.

        The live playback identity is never changed here.  When the target
        differs from the playing song the payload is marked as a preview.
        """
        if not isinstance(candidate, dict) or not candidate.get("provider"):
            return False

        artist = str(artist or "")
        title = str(title or "")
        if not title:
            return False
        try:
            duration = float(duration or 0)
        except (TypeError, ValueError):
            duration = 0.0

        app = self._app
        with app.state_lock:
            app.current_generation_id += 1
            generation_id = app.current_generation_id
            app.current_lyrics_key = _make_track_key(artist, title)
            app._pending_lyrics = None
            app._pending_translations = None

        threading.Thread(
            target=app._fetch_and_translate_lyrics,
            args=(artist, title, duration, generation_id, candidate),
            daemon=True,
        ).start()
        return True

    def save_local_lyrics(self, artist, title, lines):
        """Saves lyrics as a local .lrc and reloads if it is the current song."""
        result = lyrics_providers.save_local_lrc(artist, title, lines)
        if not result.get("ok"):
            return result

        app = self._app
        with app.state_lock:
            live_artist = app.current_artist
            live_title = app.current_title
            live_duration = app.current_duration
            matches_live = bool(title) and (
                _make_track_key(artist, title)
                == _make_track_key(live_artist, live_title)
            )
            generation_id = None
            if matches_live:
                app.current_generation_id += 1
                generation_id = app.current_generation_id
                app.current_lyrics_key = _make_track_key(artist, title)
                app._pending_lyrics = None
                app._pending_translations = None

        result["reloaded"] = matches_live
        if matches_live:
            local_candidate = {
                "provider": "local",
                "id": os.path.basename(result.get("path") or ""),
                "title": title,
                "artist": artist,
            }
            threading.Thread(
                target=app._fetch_and_translate_lyrics,
                args=(
                    live_artist,
                    live_title,
                    live_duration,
                    generation_id,
                    local_candidate,
                ),
                daemon=True,
            ).start()
        return result

    def get_lrc_folder(self):
        """Returns the folder where local .lrc files are stored."""
        return str(app_paths.get_lrc_dir())

    def open_lrc_folder(self):
        """Opens the local lyrics folder in the system file browser."""
        try:
            folder = str(app_paths.get_lrc_dir())
            if hasattr(os, "startfile"):
                os.startfile(folder)
            else:
                logger.warning("Opening folders is not supported on this platform")
                return False
            return True
        except OSError as exc:
            logger.warning("Could not open lrc folder: %s", exc)
            return False

    def get_lyrics_providers(self):
        """Returns provider metadata for the lyrics search UI."""
        return lyrics_providers.get_lyrics_providers()


class SpotifyLyricsApp:
    def __init__(self, start_minimized=False):
        self.lyrics_service = LyricsService()
        self.translator_service = TranslatorService(target_lang="en")
        self.media_listener = None
        self.window = None
        self.hotkey_thread = None
        self.discord_rpc = DiscordRPC()

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
        self._is_mini = False
        self._is_fullscreen = False
        self._pending_mini = False
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

        # Create pywebview window
        self.window = webview.create_window(
            title=APP_TITLE,
            url=html_path,
            js_api=self.api,
            width=geometry["width"],
            height=geometry["height"],
            min_size=(window_state.MIN_WIDTH, window_state.MIN_HEIGHT),
            frameless=True,
            easy_drag=True,
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
                self.window.resize(MINI_WIDTH, MINI_HEIGHT)
            if self._pending_fullscreen and self._is_fullscreen and self.window:
                self._pending_fullscreen = False
                self.window.toggle_fullscreen()
        except Exception:
            logger.exception("Could not apply the pending window mode")

    def _capture_normal_geometry(self):
        if self._is_mini or self._is_fullscreen:
            return
        geometry = self._geometry_snapshot()
        width, height = window_state.clamp_size(
            geometry.get("width"), geometry.get("height")
        )
        if width > 0 and height > 0:
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
        if self._is_fullscreen:
            return "fullscreen"
        if self._is_mini:
            return "mini"
        return "card"

    def _persist_owned(self, values):
        try:
            return window_state.persist_settings(values)
        except Exception as exc:
            logger.warning("Could not persist settings %r: %s", values, exc)
            return False

    def _save_window_state(self, include_view_mode=True):
        geometry = self._geometry_snapshot()
        width, height = window_state.clamp_size(
            geometry.get("width"), geometry.get("height")
        )
        values = {"window_width": width, "window_height": height}
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
            if self.window and self._window_is_shown():
                try:
                    self.window.resize(MINI_WIDTH, MINI_HEIGHT)
                except Exception as exc:
                    logger.warning("Could not resize into mini mode: %s", exc)
            else:
                self._pending_mini = True
        else:
            self._pending_mini = False
            geometry = dict(self._normal_geometry)
            if self.window and self._window_is_shown():
                try:
                    x, y = geometry.get("x"), geometry.get("y")
                    if x is not None and y is not None:
                        self.window.move(int(x), int(y))
                    self.window.resize(
                        int(geometry["width"]), int(geometry["height"])
                    )
                except Exception as exc:
                    logger.warning("Could not restore the normal window size: %s", exc)

        self._persist_owned(
            {"view_mode": "mini" if enabled else "card"}
        )

    def set_fullscreen_mode(self, enabled):
        enabled = bool(enabled)
        if enabled == self._is_fullscreen:
            return
        if enabled and self._is_mini:
            self.set_mini_mode(False)
        if enabled:
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
        logger.info("SpotifyLyrics is already running; exiting")
        return 0

    app = SpotifyLyricsApp(start_minimized=start_minimized)
    app.single_instance = instance
    try:
        app.start()
    except Exception:
        logger.exception("Fatal SpotifyLyrics startup error")
        return 1
    finally:
        try:
            app.shutdown()
        finally:
            instance.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
