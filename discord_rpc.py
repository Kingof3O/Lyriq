import os
import sys
import json
import struct
import time
import uuid
import logging
import threading

logger = logging.getLogger("DiscordRPC")

CLIENT_ID = "121456789012345678"  # Generic rich presence client ID

class DiscordRPC:
    def __init__(self, client_id=CLIENT_ID):
        self.client_id = client_id
        self.pipe = None
        self.connected = False
        self.enabled = True
        self.last_update = 0
        self.lock = threading.Lock()

    def connect(self):
        if self.connected or not self.enabled:
            return
        for i in range(10):
            pipe_name = rf"\\.\pipe\discord-rpc-{i}"
            try:
                self.pipe = open(pipe_name, "w+b", buffering=0)
                # Send Handshake (Opcode 0)
                handshake = json.dumps({"v": 1, "client_id": self.client_id})
                self._send(0, handshake)
                self.connected = True
                logger.info("Connected to Discord RPC IPC pipe")
                return
            except Exception:
                continue

    def _send(self, opcode, payload_str):
        if not self.pipe:
            return
        payload_bytes = payload_str.encode("utf-8")
        header = struct.pack("<II", opcode, len(payload_bytes))
        self.pipe.write(header + payload_bytes)
        self.pipe.flush()

    def update_presence(self, title, artist, lyric_line="", position=0.0):
        if not self.enabled:
            return
        now = time.time()
        if now - self.last_update < 1.0:
            return
        self.last_update = now

        with self.lock:
            if not self.connected:
                self.connect()
            if not self.connected:
                return

            try:
                state_text = f"🎵 {lyric_line[:120]}" if lyric_line else f"by {artist}"
                start_time = int(time.time() - position) if position > 0 else int(time.time())

                activity = {
                    "cmd": "SET_ACTIVITY",
                    "args": {
                        "pid": os.getpid(),
                        "activity": {
                            "details": f"{title} - {artist}"[:128],
                            "state": state_text,
                            "timestamps": {"start": start_time},
                            "assets": {
                                "large_image": "spotify",
                                "large_text": "Spotify Realtime Lyrics",
                                "small_image": "live",
                                "small_text": "Live Translated Lyrics"
                            }
                        }
                    },
                    "nonce": str(uuid.uuid4())
                }
                self._send(1, json.dumps(activity))
            except Exception as e:
                logger.debug(f"Discord update error: {e}")
                self.connected = False
                try:
                    if self.pipe:
                        self.pipe.close()
                except Exception:
                    pass
                self.pipe = None

    def clear(self):
        with self.lock:
            if not self.connected:
                return
            try:
                payload = {
                    "cmd": "SET_ACTIVITY",
                    "args": {"pid": os.getpid(), "activity": None},
                    "nonce": str(uuid.uuid4())
                }
                self._send(1, json.dumps(payload))
            except Exception:
                pass

    def close(self):
        self.clear()
        with self.lock:
            if self.pipe:
                try:
                    self.pipe.close()
                except Exception:
                    pass
            self.pipe = None
            self.connected = False
