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
from media_listener import MediaListener
from lyrics_service import LyricsService
from translator_service import TranslatorService
from romanizer import Romanizer
from discord_rpc import DiscordRPC
from cache_service import get_cache

logger = logging.getLogger("SpotifyLyrics")


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
        if self._app.window:
            self._app.window.toggle_fullscreen()

    def toggle_mini_mode(self, is_mini):
        if self._app.window:
            if is_mini:
                self._app.saved_width = self._app.window.width
                self._app.saved_height = self._app.window.height
                self._app.window.resize(560, 95)
            else:
                width = getattr(self._app, 'saved_width', 480)
                height = getattr(self._app, 'saved_height', 720)
                self._app.window.resize(width, height)

    def toggle_mini_expand(self, is_expanded):
        if self._app.window:
            if is_expanded:
                self._app.window.resize(560, 270)
            else:
                self._app.window.resize(560, 95)

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
        self._app.stop()
        if self._app.window:
            self._app.window.destroy()

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
    def __init__(self):
        self.lyrics_service = LyricsService()
        self.translator_service = TranslatorService(target_lang="en")
        self.media_listener = None
        self.window = None
        self.hotkey_thread = None
        self.discord_rpc = DiscordRPC()

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
            hwnd = ctypes.windll.user32.FindWindowW(None, "Spotify Lyrics & Translation")
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

        # Create pywebview window
        self.window = webview.create_window(
            title="Spotify Lyrics & Translation",
            url=html_path,
            js_api=self.api,
            width=480,
            height=720,
            min_size=(360, 85),
            frameless=True,
            easy_drag=True,
            on_top=False,
            transparent=False
        )

        # Replay any media/lyrics payloads that were produced while the page
        # was still loading.  The handler is idempotent.
        try:
            self.window.events.loaded += self._on_window_loaded
        except Exception as exc:
            logger.warning("Could not register window loaded handler: %s", exc)

        webview.start(debug=False)

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

if __name__ == "__main__":
    app = SpotifyLyricsApp()
    app.start()
