import asyncio
import datetime
import time
import threading
import logging
import base64
import winsdk.windows.media.control as wmc
import winsdk.windows.storage.streams as streams

logger = logging.getLogger("MediaListener")

class MediaListener:
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.thread = None
        self.loop = None
        self.spotify_session = None
        self.mgr = None
        self.timeline_token = None
        self.playback_token = None

        self.last_track_key = None
        self.cached_thumbnail = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._async_monitor())
        except Exception as e:
            logger.error(f"MediaListener loop error: {e}")

    async def _async_monitor(self):
        self.mgr = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()

        while self.running:
            try:
                sessions = self.mgr.get_sessions()
                found_session = None
                for s in sessions:
                    app_id = s.source_app_user_model_id.lower()
                    if "spotify" in app_id:
                        found_session = s
                        break

                if not found_session:
                    cur = self.mgr.get_current_session()
                    if cur and "spotify" in cur.source_app_user_model_id.lower():
                        found_session = cur

                if found_session != self.spotify_session:
                    self._unbind_events()
                    self.spotify_session = found_session
                    if self.spotify_session:
                        self._bind_events()

                if self.spotify_session:
                    await self._emit_state(is_seek=False)
                else:
                    if self.callback:
                        self.callback({"status": 0})

            except Exception as e:
                logger.debug(f"Media read error: {e}")

            await asyncio.sleep(1.2)

    def _bind_events(self):
        try:
            if self.spotify_session:
                self.timeline_token = self.spotify_session.add_timeline_properties_changed(
                    lambda sender, args: self._on_timeline_changed()
                )
                self.playback_token = self.spotify_session.add_playback_info_changed(
                    lambda sender, args: self._on_playback_changed()
                )
        except Exception as e:
            logger.debug(f"Event binding error: {e}")

    def _unbind_events(self):
        try:
            if self.spotify_session:
                if self.timeline_token:
                    self.spotify_session.remove_timeline_properties_changed(self.timeline_token)
                    self.timeline_token = None
                if self.playback_token:
                    self.spotify_session.remove_playback_info_changed(self.playback_token)
                    self.playback_token = None
        except Exception:
            pass

    def _on_timeline_changed(self):
        if self.loop and self.running and self.spotify_session:
            asyncio.run_coroutine_threadsafe(self._emit_state(is_seek=True), self.loop)

    def _on_playback_changed(self):
        if self.loop and self.running and self.spotify_session:
            asyncio.run_coroutine_threadsafe(self._emit_state(is_seek=False), self.loop)

    async def _emit_state(self, is_seek=False):
        if not self.spotify_session:
            return
        try:
            props = await self.spotify_session.try_get_media_properties_async()
            timeline = self.spotify_session.get_timeline_properties()
            info = self.spotify_session.get_playback_info()

            title = props.title or ""
            artist = props.artist or ""
            track_key = f"{artist} - {title}"

            # Only read and base64-encode thumbnail when track changes (saves CPU & memory!)
            if track_key != self.last_track_key:
                self.last_track_key = track_key
                self.cached_thumbnail = None
                if props.thumbnail:
                    try:
                        stream = await props.thumbnail.open_read_async()
                        if stream and 0 < stream.size < 2_500_000:
                            reader = streams.DataReader(stream)
                            await reader.load_async(stream.size)
                            buf = bytearray(stream.size)
                            reader.read_bytes(buf)
                            self.cached_thumbnail = "data:image/jpeg;base64," + base64.b64encode(buf).decode('ascii')
                    except Exception as e:
                        logger.debug(f"Thumbnail load error: {e}")

            status = int(info.playback_status)
            raw_pos = timeline.position.total_seconds()
            duration = timeline.end_time.total_seconds()
            last_updated = timeline.last_updated_time

            now = datetime.datetime.now(datetime.timezone.utc)
            if status == 4 and last_updated: # 4 = Playing
                elapsed = (now - last_updated).total_seconds()
                precise_pos = max(0.0, min(duration, raw_pos + elapsed))
            else:
                precise_pos = raw_pos

            data = {
                "app": "Spotify",
                "title": title,
                "artist": artist,
                "album": props.album_title or "",
                "thumbnail": self.cached_thumbnail,
                "status": status,
                "position": round(precise_pos, 2),
                "duration": round(duration, 2),
                "timestamp": round(time.time() * 1000, 1),
                "is_seek": is_seek
            }
            if self.callback:
                self.callback(data)
        except Exception:
            pass

    # Playback Controls
    async def _async_seek(self, microseconds: int):
        try:
            if self.spotify_session:
                await self.spotify_session.try_change_playback_position_async(microseconds)
        except Exception as e:
            logger.debug(f"Seek error: {e}")

    async def _async_toggle_play_pause(self):
        try:
            if self.spotify_session:
                await self.spotify_session.try_toggle_play_pause_async()
        except Exception as e:
            logger.debug(f"Toggle play pause error: {e}")

    async def _async_next_track(self):
        try:
            if self.spotify_session:
                await self.spotify_session.try_skip_next_async()
        except Exception as e:
            logger.debug(f"Next track error: {e}")

    async def _async_prev_track(self):
        try:
            if self.spotify_session:
                await self.spotify_session.try_skip_previous_async()
        except Exception as e:
            logger.debug(f"Prev track error: {e}")

    def seek(self, seconds: float):
        if self.spotify_session and self.loop and self.loop.is_running():
            microseconds = int(seconds * 10_000_000)
            asyncio.run_coroutine_threadsafe(self._async_seek(microseconds), self.loop)

    def toggle_play_pause(self):
        if self.spotify_session and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_toggle_play_pause(), self.loop)

    def next_track(self):
        if self.spotify_session and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_next_track(), self.loop)

    def prev_track(self):
        if self.spotify_session and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_prev_track(), self.loop)

    def stop(self):
        self.running = False
        self._unbind_events()
