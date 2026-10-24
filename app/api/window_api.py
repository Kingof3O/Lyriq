"""Window control, pin, ghost mode, and view mode switching APIs."""

import ctypes
import logging

logger = logging.getLogger("WindowAPI")
user32 = ctypes.windll.user32


class WindowAPIMixin:
    def toggle_pin(self, is_pinned):
        self._app._persist_owned({"always_on_top": bool(is_pinned)})
        try:
            hwnd = self._app.get_hwnd()
            if hwnd:
                HWND_TOPMOST = -1
                HWND_NOTOPMOST = -2
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOACTIVATE = 0x0010
                h_after = HWND_TOPMOST if is_pinned else HWND_NOTOPMOST
                user32.SetWindowPos(
                    int(hwnd),
                    h_after,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                )
        except Exception as e:
            logger.warning("Toggle pin error: %s", e)

    def toggle_fullscreen(self):
        self._app.set_fullscreen_mode(not self._app.is_fullscreen)

    def toggle_mini_mode(self, is_mini):
        self._app.set_mini_mode(bool(is_mini))

    def toggle_mini_expand(self, is_expanded):
        self._app.set_mini_expand(bool(is_expanded))

    def set_mini_width(self, width):
        return self._app.set_mini_width(width)

    def get_mini_width(self):
        return self._app._mini_width

    def toggle_square_mode(self, is_square):
        self._app.set_square_mode(bool(is_square))

    def set_square_size(self, size):
        return self._app.set_square_size(size)

    def get_square_size(self):
        return self._app._square_size

    def toggle_ghost_mode(self, is_ghost):
        """Click-through mode: clicks pass through to background window."""
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
            logger.warning("Ghost mode toggle error: %s", e)

    def minimize(self):
        if self._app.window:
            self._app.window.minimize()

    def close(self):
        if self._app.close_to_tray:
            self._app.hide_to_tray()
            return True
        self._app.request_quit()
        return True

    def quit(self):
        self._app.request_quit()
        return True
