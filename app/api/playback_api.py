"""Playback transport and audio volume APIs."""

import ctypes
import logging
import threading

logger = logging.getLogger("PlaybackAPI")


class PlaybackAPIMixin:
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

    def adjust_volume(self, delta):
        """Adjusts Spotify's individual volume directly via Core Audio (WASAPI).
        Falls back to Windows master volume if Spotify session is not found."""
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            sessions = AudioUtilities.GetAllSessions()
            for s in sessions:
                proc = s.Process
                if proc and "spotify" in proc.name().lower():
                    vol = s._ctl.QueryInterface(ISimpleAudioVolume)
                    cur = vol.GetMasterVolume()
                    step = 0.05 if delta > 0 else -0.05
                    new_vol = max(0.0, min(1.0, cur + step))
                    vol.SetMasterVolume(new_vol, None)
                    return {"target": "spotify", "volume": int(round(new_vol * 100))}
        except Exception as e:
            logger.debug("Spotify direct volume error: %s", e)

        # Fallback to Windows master volume
        try:
            user32 = ctypes.windll.user32
            VK_VOLUME_UP = 0xAF
            VK_VOLUME_DOWN = 0xAE
            vk = VK_VOLUME_UP if delta > 0 else VK_VOLUME_DOWN
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
            return {"target": "master", "volume": None}
        except Exception as e:
            logger.warning("Volume adjust error: %s", e)
            return {"target": "error", "volume": None}

    def set_volume(self, percent):
        """Sets Spotify's application volume directly (0 to 100)."""
        try:
            percent = max(0.0, min(100.0, float(percent)))
            fraction = percent / 100.0
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            sessions = AudioUtilities.GetAllSessions()
            for s in sessions:
                proc = s.Process
                if proc and "spotify" in proc.name().lower():
                    vol = s._ctl.QueryInterface(ISimpleAudioVolume)
                    vol.SetMasterVolume(fraction, None)
                    return {"target": "spotify", "volume": int(round(percent))}
        except Exception as e:
            logger.debug("Spotify direct set volume error: %s", e)
        return {"target": "error", "volume": None}

    def get_volume(self):
        """Gets Spotify's current volume percentage (0 to 100)."""
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            sessions = AudioUtilities.GetAllSessions()
            for s in sessions:
                proc = s.Process
                if proc and "spotify" in proc.name().lower():
                    vol = s._ctl.QueryInterface(ISimpleAudioVolume)
                    return {"target": "spotify", "volume": int(round(vol.GetMasterVolume() * 100))}
        except Exception:
            pass
        return {"target": "spotify", "volume": 100}

    def get_spotify_queue(self):
        """Fetches the live upcoming playback queue from Spotify Web API if configured."""
        token = self._app.lyrics_service.cache.get_setting("spotify_token", "").strip()
        if not token:
            return {
                "connected": False,
                "items": [],
                "message": "Spotify API token is not configured. Add your Spotify Access Token in Settings -> Integrations to view your live upcoming queue."
            }

        import urllib.request
        import json
        req = urllib.request.Request(
            "https://api.spotify.com/v1/me/player/queue",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "Lyriq/3.0.0"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    queue_raw = data.get("queue") or []
                    items = []
                    for t in queue_raw:
                        images = t.get("album", {}).get("images", [])
                        thumb = images[0].get("url") if images else ""
                        artists = ", ".join(a.get("name", "") for a in t.get("artists", []))
                        dur_sec = round(t.get("duration_ms", 0) / 1000)
                        items.append({
                            "title": t.get("name", "Unknown Title"),
                            "artist": artists,
                            "album": t.get("album", {}).get("name", ""),
                            "thumbnail": thumb,
                            "duration_seconds": dur_sec,
                            "uri": t.get("uri", "")
                        })
                    return {"connected": True, "items": items, "message": ""}
                elif resp.status == 401:
                    return {"connected": False, "items": [], "message": "Spotify token has expired. Please refresh your token in Settings -> Integrations."}
        except Exception as exc:
            logger.debug("Spotify queue request error: %s", exc)
            return {"connected": False, "items": [], "message": f"Could not reach Spotify Web API: {exc}"}
        return {"connected": False, "items": [], "message": "Could not retrieve queue."}

    def set_spotify_token(self, token):
        """Saves Spotify access token to settings."""
        self._app.lyrics_service.cache.save_setting("spotify_token", str(token).strip())
        return True

    def set_sleep_timer(self, minutes):
        """Auto-pause Spotify after specified minutes."""
        if hasattr(self, "_sleep_timer") and self._sleep_timer:
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
