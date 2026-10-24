"""Single-instance guard using a named Windows mutex."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import sys
import time

logger = logging.getLogger("SingleInstance")

MUTEX_NAME = r"Local\SpotifyLyrics_v3"
DEFAULT_WINDOW_TITLE = "Spotify Lyrics & Translation"
ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9


class SingleInstance:
    """Own a process-wide named mutex and focus the first window on duplicates."""

    def __init__(
        self,
        name=MUTEX_NAME,
        window_title=DEFAULT_WINDOW_TITLE,
        focus_timeout=3.0,
    ):
        self.name = name
        self.window_title = window_title
        self.focus_timeout = max(0.0, float(focus_timeout))
        self._handle = None

    def acquire(self):
        """Return True when this process owns the mutex.

        On failure to create the mutex the guard fails open: refusing to start
        would make a Windows API hiccup permanently fatal for the app.
        """
        if sys.platform != "win32":
            return True
        if self._handle is not None:
            return True

        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.argtypes = [
                ctypes.wintypes.LPVOID,
                ctypes.wintypes.BOOL,
                ctypes.wintypes.LPCWSTR,
            ]
            kernel32.CreateMutexW.restype = ctypes.wintypes.HANDLE
            kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
            kernel32.CloseHandle.restype = ctypes.wintypes.BOOL

            handle = kernel32.CreateMutexW(None, False, self.name)
            error = ctypes.get_last_error()
        except Exception as exc:
            logger.warning("Could not create the single-instance mutex: %s", exc)
            return True

        if not handle:
            logger.warning(
                "CreateMutexW failed for %s (error %s); starting without the guard",
                self.name,
                error,
            )
            return True

        if error == ERROR_ALREADY_EXISTS:
            try:
                kernel32.CloseHandle(handle)
            except Exception:
                pass
            logger.info("Another SpotifyLyrics instance already owns the mutex")
            self._focus_existing_window()
            return False

        self._handle = handle
        logger.debug("Acquired single-instance mutex %s", self.name)
        return True

    def release(self):
        """Close the mutex handle.  Safe to call more than once."""
        handle = self._handle
        self._handle = None
        if handle is None or sys.platform != "win32":
            return
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
            kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
            kernel32.CloseHandle(handle)
        except Exception as exc:
            logger.warning("Could not release the single-instance mutex: %s", exc)

    def _focus_existing_window(self):
        if sys.platform != "win32":
            return False
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.FindWindowW.argtypes = [
                ctypes.wintypes.LPCWSTR,
                ctypes.wintypes.LPCWSTR,
            ]
            user32.FindWindowW.restype = ctypes.wintypes.HWND
            user32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
            user32.ShowWindow.restype = ctypes.wintypes.BOOL
            user32.SetForegroundWindow.argtypes = [ctypes.wintypes.HWND]
            user32.SetForegroundWindow.restype = ctypes.wintypes.BOOL
        except Exception as exc:
            logger.warning("Could not prepare window focusing calls: %s", exc)
            return False

        deadline = time.monotonic() + self.focus_timeout
        hwnd = None
        while True:
            try:
                hwnd = user32.FindWindowW(None, self.window_title)
            except Exception as exc:
                logger.warning("Could not look up the existing window: %s", exc)
                return False
            if hwnd:
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(0.2)

        if not hwnd:
            logger.warning(
                "The first instance did not expose a window titled %r within %.1fs",
                self.window_title,
                self.focus_timeout,
            )
            return False

        try:
            user32.ShowWindow(hwnd, SW_RESTORE)
            if not user32.SetForegroundWindow(hwnd):
                logger.debug("SetForegroundWindow was rejected by Windows")
            return True
        except Exception as exc:
            logger.warning("Could not focus the existing window: %s", exc)
            return False
