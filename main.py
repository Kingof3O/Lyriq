import os
import sys
import json
import time
import threading
import ctypes
import ctypes.wintypes
import urllib.parse
import urllib.request
import webview

from media_listener import MediaListener
from lyrics_service import LyricsService
from translator_service import TranslatorService
from romanizer import Romanizer
from discord_rpc import DiscordRPC

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

    # Song History & Favorites
    def toggle_favorite(self, artist, title):
        return self._app.lyrics_service.cache.toggle_favorite(artist, title)

    def get_song_history(self):
        return self._app.lyrics_service.cache.get_song_history()

    def load_history_song(self, artist, title):
        if artist and title:
            threading.Thread(target=self._app._fetch_and_translate_lyrics, args=(artist, title, 0), daemon=True).start()

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


class SpotifyLyricsApp:
    def __init__(self):
        self.lyrics_service = LyricsService()
        self.translator_service = TranslatorService(target_lang="en")
        self.media_listener = None
        self.window = None
        self.hotkey_thread = None
        self.discord_rpc = DiscordRPC()

        self.current_track = None
        self.current_lyrics = None
        self.last_sync_time = 0
        self.last_position = 0
        self.playback_status = 0
        self.is_fetching = False

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

    def on_media_update(self, data):
        if not data:
            return

        title = data.get("title", "")
        artist = data.get("artist", "")
        album = data.get("album", "")
        status = data.get("status", 0)
        pos = data.get("position", 0.0)
        duration = data.get("duration", 0.0)
        is_seek = data.get("is_seek", False)

        self.last_position = pos
        self.last_sync_time = time.time()
        self.playback_status = status

        track_key = f"{artist} - {title}"

        # If track changed
        if track_key != self.current_track:
            self.current_track = track_key
            self.current_lyrics = None

            # Record in persistent history
            if title and artist:
                self.lyrics_service.cache.record_song_play(artist, title, album, data.get("thumbnail", ""))

            # Attach is_favorite status
            data["is_favorite"] = self.lyrics_service.cache.is_favorite(artist, title)

            # Update track info & thumbnail immediately
            self.evaluate_js(f"window.updateTrack({json.dumps(data)})")

            if title and artist:
                threading.Thread(target=self._fetch_and_translate_lyrics, args=(artist, title, duration), daemon=True).start()
        else:
            data["is_favorite"] = self.lyrics_service.cache.is_favorite(artist, title)
            self.evaluate_js(f"window.updateTrack({json.dumps(data)})")

        # Discord Rich Presence Update
        if title and artist and status == 4:
            self.discord_rpc.update_presence(title, artist, "", pos)
        elif status == 5:
            self.discord_rpc.clear()

    def _fetch_and_translate_lyrics(self, artist, title, duration):
        if self.is_fetching:
            return
        self.is_fetching = True
        try:
            # 1. Fetch Synced Lyrics
            lyrics_data = self.lyrics_service.fetch_lyrics(artist, title, duration)
            if not lyrics_data or not lyrics_data.get("lines"):
                self.evaluate_js("window.updateLyrics(null)")
                return

            raw_lines = lyrics_data["lines"]

            # 2. INSTANT DISPLAY
            initial_payload = {
                "title": lyrics_data.get("title"),
                "artist": lyrics_data.get("artist"),
                "is_synced": lyrics_data.get("is_synced", True),
                "lang": "unknown",
                "lines": raw_lines
            }
            self.evaluate_js(f"window.updateLyrics({json.dumps(initial_payload)})")

            # 3. BACKGROUND TRANSLATION & PHONETICS
            translated_lines, dominant_lang = self.translator_service.translate_lines(raw_lines)
            
            # 4. Stream translations + romanizations into rendered lines
            trans_payload = {
                "lang": dominant_lang,
                "lines": translated_lines
            }
            self.evaluate_js(f"window.updateTranslations({json.dumps(trans_payload)})")

        except Exception as e:
            print(f"Lyrics/Translation error: {e}")
            self.evaluate_js("window.updateLyrics(null)")
        finally:
            self.is_fetching = False

    def reload_current_lyrics(self):
        if self.current_track and " - " in self.current_track:
            artist, title = self.current_track.split(" - ", 1)
            threading.Thread(target=self._fetch_and_translate_lyrics, args=(artist, title, 0), daemon=True).start()

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
