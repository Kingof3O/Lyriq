"""Native Windows system tray icon implemented with ctypes only.

A small hidden top-level window owns the ``Shell_NotifyIconW`` notification and
pumps its own message loop on a daemon thread.  A top-level (but never shown)
window is used instead of a ``HWND_MESSAGE`` window because message-only
windows do not receive the broadcast ``TaskbarCreated`` message that is needed
to re-add the icon after Explorer restarts.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import os
import sys
import threading

logger = logging.getLogger("TrayIcon")

_WINDOWS = sys.platform == "win32"

WM_NULL = 0x0000
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_CONTEXTMENU = 0x007B
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_APP = 0x8000

WS_POPUP = 0x80000000
WS_EX_TOOLWINDOW = 0x00000080

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x00000010
LR_DEFAULTSIZE = 0x00000040
IDI_APPLICATION = 32512

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002

SW_HIDE = 0
SW_RESTORE = 9

MENU_SHOW_HIDE = 1001
MENU_PLAY_PAUSE = 1002
MENU_MINI = 1003
MENU_SQUARE = 1006
MENU_SETTINGS = 1004
MENU_QUIT = 1005

ACTION_SHOW_HIDE = "show_hide"
ACTION_PLAY_PAUSE = "play_pause"
ACTION_MINI = "mini"
ACTION_SQUARE = "square"
ACTION_SETTINGS = "settings"
ACTION_QUIT = "quit"

_MENU_ACTIONS = {
    MENU_SHOW_HIDE: ACTION_SHOW_HIDE,
    MENU_PLAY_PAUSE: ACTION_PLAY_PAUSE,
    MENU_MINI: ACTION_MINI,
    MENU_SQUARE: ACTION_SQUARE,
    MENU_SETTINGS: ACTION_SETTINGS,
    MENU_QUIT: ACTION_QUIT,
}

WM_TRAYICON = WM_APP + 1

try:
    WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t,
        ctypes.wintypes.HWND,
        ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    )
except AttributeError:  # pragma: no cover - non-Windows import safety
    WNDPROC = ctypes.CFUNCTYPE(
        ctypes.c_ssize_t,
        ctypes.wintypes.HWND,
        ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    )


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.wintypes.DWORD),
        ("Data2", ctypes.wintypes.WORD),
        ("Data3", ctypes.wintypes.WORD),
        ("Data4", ctypes.wintypes.BYTE * 8),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.wintypes.HINSTANCE),
        ("hIcon", ctypes.wintypes.HICON),
        ("hCursor", ctypes.wintypes.HANDLE),
        ("hbrBackground", ctypes.wintypes.HBRUSH),
        ("lpszMenuName", ctypes.wintypes.LPCWSTR),
        ("lpszClassName", ctypes.wintypes.LPCWSTR),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("hWnd", ctypes.wintypes.HWND),
        ("uID", ctypes.wintypes.UINT),
        ("uFlags", ctypes.wintypes.UINT),
        ("uCallbackMessage", ctypes.wintypes.UINT),
        ("hIcon", ctypes.wintypes.HICON),
        ("szTip", ctypes.wintypes.WCHAR * 128),
        ("dwState", ctypes.wintypes.DWORD),
        ("dwStateMask", ctypes.wintypes.DWORD),
        ("szInfo", ctypes.wintypes.WCHAR * 256),
        ("uVersion", ctypes.wintypes.UINT),
        ("szInfoTitle", ctypes.wintypes.WCHAR * 64),
        ("dwInfoFlags", ctypes.wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", ctypes.wintypes.HICON),
    ]


class TrayIcon:
    """Tray icon whose menu actions are reported through ``on_action``."""

    def __init__(self, on_action, icon_path=None, tooltip="Spotify Lyrics"):
        self.on_action = on_action
        self.icon_path = icon_path
        self.tooltip = tooltip
        self._thread = None
        self._ready = threading.Event()
        self._hwnd = None
        self._icon_added = False
        self._icon_handle = None
        self._owns_icon = False
        self._taskbar_created = 0
        self._wndproc = None
        self._user32 = None
        self._shell32 = None
        self._kernel32 = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self):
        """Start the tray thread and wait briefly for the icon window."""
        if not _WINDOWS:
            logger.warning("Tray icons are only supported on Windows")
            return False
        if self._thread is not None and self._thread.is_alive():
            return bool(self._icon_added)

        self._ready.clear()
        self._thread = threading.Thread(
            target=self._run, name="SpotifyLyricsTray", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(3.0):
            logger.warning("Timed out while creating the tray icon")
            return False
        return self._hwnd is not None and self._icon_added

    def stop(self, timeout=3.0):
        """Ask the tray thread to remove the icon and exit."""
        if not _WINDOWS:
            return
        hwnd = self._hwnd
        if hwnd:
            try:
                user32 = self._user32 or ctypes.WinDLL("user32", use_last_error=True)
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            except Exception as exc:
                logger.warning("Could not post the tray close message: %s", exc)

        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout)
            if thread.is_alive():
                logger.warning("Tray thread did not exit within %.1fs", timeout)
                self._remove_icon()
        self._thread = None

    # ------------------------------------------------------------------
    # Win32 plumbing
    # ------------------------------------------------------------------
    def _load_libraries(self):
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        u = self._user32
        u.DefWindowProcW.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.wintypes.UINT,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM,
        ]
        u.DefWindowProcW.restype = ctypes.c_ssize_t
        u.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
        u.RegisterClassW.restype = ctypes.wintypes.ATOM
        u.UnregisterClassW.argtypes = [
            ctypes.wintypes.LPCWSTR,
            ctypes.wintypes.HINSTANCE,
        ]
        u.UnregisterClassW.restype = ctypes.wintypes.BOOL
        u.CreateWindowExW.argtypes = [
            ctypes.wintypes.DWORD,
            ctypes.wintypes.LPCWSTR,
            ctypes.wintypes.LPCWSTR,
            ctypes.wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.wintypes.HWND,
            ctypes.wintypes.HMENU,
            ctypes.wintypes.HINSTANCE,
            ctypes.wintypes.LPVOID,
        ]
        u.CreateWindowExW.restype = ctypes.wintypes.HWND
        u.DestroyWindow.argtypes = [ctypes.wintypes.HWND]
        u.DestroyWindow.restype = ctypes.wintypes.BOOL
        u.PostMessageW.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.wintypes.UINT,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM,
        ]
        u.PostMessageW.restype = ctypes.wintypes.BOOL
        u.GetMessageW.argtypes = [
            ctypes.POINTER(ctypes.wintypes.MSG),
            ctypes.wintypes.HWND,
            ctypes.wintypes.UINT,
            ctypes.wintypes.UINT,
        ]
        u.GetMessageW.restype = ctypes.wintypes.BOOL
        u.TranslateMessage.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG)]
        u.TranslateMessage.restype = ctypes.wintypes.BOOL
        u.DispatchMessageW.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG)]
        u.DispatchMessageW.restype = ctypes.c_ssize_t
        u.RegisterWindowMessageW.argtypes = [ctypes.wintypes.LPCWSTR]
        u.RegisterWindowMessageW.restype = ctypes.wintypes.UINT
        u.LoadImageW.argtypes = [
            ctypes.wintypes.HINSTANCE,
            ctypes.wintypes.LPCWSTR,
            ctypes.wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.wintypes.UINT,
        ]
        u.LoadImageW.restype = ctypes.wintypes.HANDLE
        u.LoadIconW.argtypes = [ctypes.wintypes.HINSTANCE, ctypes.c_void_p]
        u.LoadIconW.restype = ctypes.wintypes.HICON
        u.DestroyIcon.argtypes = [ctypes.wintypes.HICON]
        u.DestroyIcon.restype = ctypes.wintypes.BOOL
        u.CreatePopupMenu.restype = ctypes.wintypes.HMENU
        u.AppendMenuW.argtypes = [
            ctypes.wintypes.HMENU,
            ctypes.wintypes.UINT,
            ctypes.c_size_t,
            ctypes.wintypes.LPCWSTR,
        ]
        u.AppendMenuW.restype = ctypes.wintypes.BOOL
        u.TrackPopupMenuEx.argtypes = [
            ctypes.wintypes.HMENU,
            ctypes.wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.wintypes.HWND,
            ctypes.wintypes.LPVOID,
        ]
        u.TrackPopupMenuEx.restype = ctypes.wintypes.UINT
        u.DestroyMenu.argtypes = [ctypes.wintypes.HMENU]
        u.DestroyMenu.restype = ctypes.wintypes.BOOL
        u.GetCursorPos.argtypes = [ctypes.POINTER(ctypes.wintypes.POINT)]
        u.GetCursorPos.restype = ctypes.wintypes.BOOL
        u.SetForegroundWindow.argtypes = [ctypes.wintypes.HWND]
        u.SetForegroundWindow.restype = ctypes.wintypes.BOOL
        u.IsWindowVisible.argtypes = [ctypes.wintypes.HWND]
        u.IsWindowVisible.restype = ctypes.wintypes.BOOL

        self._shell32.Shell_NotifyIconW.argtypes = [
            ctypes.wintypes.DWORD,
            ctypes.POINTER(NOTIFYICONDATAW),
        ]
        self._shell32.Shell_NotifyIconW.restype = ctypes.wintypes.BOOL

        self._kernel32.GetModuleHandleW.argtypes = [ctypes.wintypes.LPCWSTR]
        self._kernel32.GetModuleHandleW.restype = ctypes.wintypes.HINSTANCE

    def _run(self):
        hwnd = None
        class_name = None
        try:
            self._load_libraries()
            instance = self._kernel32.GetModuleHandleW(None)
            class_name = f"SpotifyLyricsTray_{os.getpid()}_{id(self):x}"

            self._wndproc = WNDPROC(self._wnd_proc)
            window_class = WNDCLASSW()
            window_class.lpfnWndProc = self._wndproc
            window_class.hInstance = instance
            window_class.lpszClassName = class_name
            if not self._user32.RegisterClassW(ctypes.byref(window_class)):
                logger.warning(
                    "Could not register the tray window class (error %s)",
                    ctypes.get_last_error(),
                )
                return

            self._taskbar_created = self._user32.RegisterWindowMessageW(
                "TaskbarCreated"
            )
            hwnd = self._user32.CreateWindowExW(
                WS_EX_TOOLWINDOW,
                class_name,
                "Spotify Lyrics Tray",
                WS_POPUP,
                0,
                0,
                0,
                0,
                None,
                None,
                instance,
                None,
            )
            if not hwnd:
                logger.warning(
                    "Could not create the tray window (error %s)",
                    ctypes.get_last_error(),
                )
                return

            self._hwnd = hwnd
            self._icon_handle = self._load_icon()
            if not self._add_icon():
                logger.warning("Could not add the tray icon")
            self._ready.set()

            message = ctypes.wintypes.MSG()
            while True:
                result = self._user32.GetMessageW(
                    ctypes.byref(message), None, 0, 0
                )
                if result <= 0:
                    break
                self._user32.TranslateMessage(ctypes.byref(message))
                self._user32.DispatchMessageW(ctypes.byref(message))
        except Exception:
            logger.exception("Tray thread failed")
        finally:
            self._remove_icon()
            self._destroy_icon()
            self._hwnd = None
            if class_name is not None and self._user32 is not None:
                try:
                    self._user32.UnregisterClassW(
                        class_name,
                        self._kernel32.GetModuleHandleW(None),
                    )
                except Exception:
                    pass
            self._ready.set()

    def _wnd_proc(self, hwnd, message, wparam, lparam):
        try:
            if (
                self._taskbar_created
                and message == self._taskbar_created
            ):
                # Explorer restarted; the old icon registration is gone.
                self._icon_added = False
                self._add_icon()
                return 0

            if message == WM_TRAYICON:
                event = int(lparam) & 0xFFFF
                if event == WM_LBUTTONUP:
                    self._emit(ACTION_SHOW_HIDE)
                    return 0
                if event == WM_RBUTTONUP:
                    self._show_menu()
                    return 0
                return 0

            if message == WM_CLOSE:
                self._remove_icon()
                self._user32.DestroyWindow(hwnd)
                return 0

            if message == WM_DESTROY:
                self._remove_icon()
                self._user32.PostQuitMessage(0)
                return 0
        except Exception:
            logger.exception("Tray window procedure failed")

        return self._user32.DefWindowProcW(hwnd, message, wparam, lparam)

    # ------------------------------------------------------------------
    # Icon and menu
    # ------------------------------------------------------------------
    def _load_icon(self):
        if self.icon_path and os.path.isfile(self.icon_path):
            handle = self._user32.LoadImageW(
                None,
                self.icon_path,
                IMAGE_ICON,
                0,
                0,
                LR_LOADFROMFILE | LR_DEFAULTSIZE,
            )
            if handle:
                self._owns_icon = True
                return handle
            logger.warning(
                "Could not load tray icon %s (error %s)",
                self.icon_path,
                ctypes.get_last_error(),
            )

        handle = self._user32.LoadIconW(
            None, ctypes.c_void_p(IDI_APPLICATION)
        )
        self._owns_icon = False
        if not handle:
            logger.warning("Could not load the fallback tray icon")
        return handle

    def _add_icon(self):
        if not self._hwnd or not self._icon_handle:
            return False
        with self._lock:
            data = NOTIFYICONDATAW()
            data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            data.hWnd = self._hwnd
            data.uID = 1
            data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            data.uCallbackMessage = WM_TRAYICON
            data.hIcon = self._icon_handle
            data.szTip = self.tooltip[:127]
            if self._shell32.Shell_NotifyIconW(
                NIM_ADD, ctypes.byref(data)
            ):
                self._icon_added = True
                return True
            # The icon can already exist (for example a duplicate
            # TaskbarCreated notification); refresh it in place.
            if self._shell32.Shell_NotifyIconW(
                NIM_MODIFY, ctypes.byref(data)
            ):
                self._icon_added = True
                return True
            self._icon_added = False
            return False

    def _remove_icon(self):
        hwnd = self._hwnd
        if not hwnd or not self._icon_added:
            return
        with self._lock:
            if not self._icon_added:
                return
            data = NOTIFYICONDATAW()
            data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            data.hWnd = hwnd
            data.uID = 1
            try:
                if not self._shell32.Shell_NotifyIconW(
                    NIM_DELETE, ctypes.byref(data)
                ):
                    logger.debug("Shell_NotifyIconW(NIM_DELETE) failed")
            except Exception as exc:
                logger.debug("Could not remove the tray icon: %s", exc)
            finally:
                self._icon_added = False

    def _destroy_icon(self):
        handle = self._icon_handle
        self._icon_handle = None
        if handle and self._owns_icon:
            try:
                self._user32.DestroyIcon(handle)
            except Exception:
                pass

    def _show_menu(self):
        user32 = self._user32
        menu = user32.CreatePopupMenu()
        if not menu:
            logger.warning("Could not create the tray menu")
            return

        try:
            user32.AppendMenuW(menu, MF_STRING, MENU_SHOW_HIDE, "Show / Hide")
            user32.AppendMenuW(menu, MF_STRING, MENU_PLAY_PAUSE, "Play / Pause")
            user32.AppendMenuW(menu, MF_STRING, MENU_MINI, "Mini mode")
            user32.AppendMenuW(menu, MF_STRING, MENU_SQUARE, "Square mode")
            user32.AppendMenuW(menu, MF_STRING, MENU_SETTINGS, "Settings")
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, MENU_QUIT, "Quit")

            point = ctypes.wintypes.POINT()
            if not user32.GetCursorPos(ctypes.byref(point)):
                logger.warning("Could not read the cursor position for the tray menu")
                return

            # Required so the popup dismisses when the user clicks elsewhere.
            user32.SetForegroundWindow(self._hwnd)
            command = user32.TrackPopupMenuEx(
                menu,
                TPM_RETURNCMD | TPM_RIGHTBUTTON,
                point.x,
                point.y,
                self._hwnd,
                None,
            )
            user32.PostMessageW(self._hwnd, WM_NULL, 0, 0)
            action = _MENU_ACTIONS.get(command)
            if action:
                self._emit(action)
        finally:
            user32.DestroyMenu(menu)

    def _emit(self, action):
        if not self.on_action:
            return
        try:
            self.on_action(action)
        except Exception:
            logger.exception("Tray action %r failed", action)
