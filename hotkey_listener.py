"""Global Windows hotkey listener thread using ctypes and Win32 RegisterHotKey."""

import ctypes
import ctypes.wintypes
import threading


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
        # ID 6: Ctrl + Shift + S -> Square Mode
        user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x47)  # 'G'
        user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x4D)  # 'M'
        user32.RegisterHotKey(None, 3, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x48)  # 'H'
        user32.RegisterHotKey(None, 4, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x4C)  # 'L'
        user32.RegisterHotKey(None, 5, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x20)  # VK_SPACE
        user32.RegisterHotKey(None, 6, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x53)  # 'S'

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

        for hid in range(1, 7):
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
