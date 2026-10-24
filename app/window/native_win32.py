"""Native Win32 and WinForms interop helpers."""

import ctypes
import logging

logger = logging.getLogger("NativeWin32")
user32 = ctypes.windll.user32
APP_TITLE = "Spotify Lyrics"


def get_hwnd(window):
    """Retrieves the Windows HWND handle from the pywebview window."""
    try:
        if window and hasattr(window, "native") and window.native:
            handle = getattr(window.native, "Handle", None)
            if handle is not None:
                if hasattr(handle, "ToInt64"):
                    return handle.ToInt64()
                elif hasattr(handle, "ToInt32"):
                    return handle.ToInt32()
                elif isinstance(handle, int):
                    return handle
    except Exception:
        pass
    try:
        hwnd = user32.FindWindowW(None, APP_TITLE)
        if hwnd:
            return hwnd
    except Exception:
        pass
    return None


def update_native_min_size(window, min_w, min_h):
    """Updates the underlying WinForms Form.MinimumSize dynamically."""
    try:
        if not window:
            return
        window.min_size = (int(min_w), int(min_h))
        native = getattr(window, "native", None)
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


def toggle_show_hide(hwnd):
    """Toggles window visibility between SW_HIDE and SW_RESTORE."""
    try:
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
        logger.warning("Toggle show/hide error: %s", e)


def show_window(hwnd):
    """Restores and brings the window to the foreground."""
    try:
        if not hwnd:
            return False
        SW_RESTORE = 9
        user32.ShowWindow(ctypes.c_void_p(hwnd), SW_RESTORE)
        user32.SetForegroundWindow(ctypes.c_void_p(hwnd))
        return True
    except Exception as exc:
        logger.warning("Could not restore/foreground window: %s", exc)
        return False
