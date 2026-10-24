import os
import sys
import json
import struct
import time
import uuid
import logging
import threading

logger = logging.getLogger("DiscordRPC")

# Default registered Rich Presence client ID
DEFAULT_CLIENT_ID = "1563650212957003939"

class DiscordRPC:
    def __init__(self, client_id=DEFAULT_CLIENT_ID):
        self.client_id = str(client_id).strip() or DEFAULT_CLIENT_ID
        self.pipe = None
        self.connected = False
        self.enabled = True
        self.last_update = 0
        self.lock = threading.Lock()

    def set_client_id(self, client_id: str):
        with self.lock:
            cid = str(client_id).strip() or DEFAULT_CLIENT_ID
            if cid != self.client_id:
                self.client_id = cid
                if self.connected:
                    self.close()

    def connect(self):
        if self.connected or not self.enabled:
            return
        for i in range(10):
            pipe_name = rf"\\.\pipe\discord-ipc-{i}"
            try:
                self.pipe = open(pipe_name, "w+b", buffering=0)
                # Send Handshake (Opcode 0)
                handshake = json.dumps({"v": 1, "client_id": self.client_id}).encode("utf-8")
                header = struct.pack("<II", 0, len(handshake))
                self.pipe.write(header + handshake)
                self.pipe.flush()

                # Read handshake response
                resp_header = self.pipe.read(8)
                if resp_header and len(resp_header) == 8:
                    op, length = struct.unpack("<II", resp_header)
                    resp_bytes = self.pipe.read(length)
                    if op == 1:
                        self.connected = True
                        logger.info("Connected to Discord IPC pipe: %s", pipe_name)
                        return
                    else:
                        logger.debug("Discord handshake returned non-ready op: %s", op)
                self.pipe.close()
                self.pipe = None
            except Exception as e:
                if self.pipe:
                    try:
                        self.pipe.close()
                    except Exception:
                        pass
                self.pipe = None
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
                state_text = f"{lyric_line[:120]}" if lyric_line else f"by {artist}"
                start_time = int(time.time() - position) if position > 0 else int(time.time())

                activity = {
                    "cmd": "SET_ACTIVITY",
                    "args": {
                        "pid": os.getpid(),
                        "activity": {
                            "details": f"{title} - {artist}"[:128],
                            "state": state_text[:128],
                            "timestamps": {"start": start_time},
                            "assets": {
                                "large_text": "Lyriq - Synchronized Lyrics"
                            }
                        }
                    },
                    "nonce": str(uuid.uuid4())
                }
                self._send(1, json.dumps(activity))
            except Exception as e:
                logger.debug("Discord update error: %s", e)
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
