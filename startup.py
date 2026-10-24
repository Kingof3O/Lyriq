"""Start-with-Windows integration via the per-user Run registry key."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger("Startup")

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "SpotifyLyrics"
START_MINIMIZED_ARG = "--minimized"


def _pythonw_executable():
    executable = Path(sys.executable)
    if executable.name.lower() == "python.exe":
        pythonw = executable.with_name("pythonw.exe")
        if pythonw.is_file():
            return str(pythonw)
    return str(executable)


def get_startup_command():
    """Return the command Windows will run for this installation."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" {START_MINIMIZED_ARG}'
    main_script = Path(__file__).resolve().with_name("main.py")
    return f'"{_pythonw_executable()}" "{main_script}" {START_MINIMIZED_ARG}'


def is_start_with_windows():
    """True when the per-user Run entry exists."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
    except ImportError:
        return False

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(str(value).strip())
    except FileNotFoundError:
        return False
    except OSError as exc:
        logger.warning("Could not read the startup registry value: %s", exc)
        return False


def set_start_with_windows(enabled):
    """Enable or disable launch at sign-in.  Returns True on success."""
    if sys.platform != "win32":
        logger.warning("Start with Windows is only supported on Windows")
        return False

    try:
        import winreg
    except ImportError:
        logger.warning("winreg is unavailable; cannot change startup behaviour")
        return False

    enabled = bool(enabled)
    try:
        if enabled:
            command = get_startup_command()
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)
            logger.info("Enabled start with Windows: %s", command)
            return True

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, VALUE_NAME)
            logger.info("Disabled start with Windows")
        except FileNotFoundError:
            # Already disabled is a successful outcome.
            pass
        return True
    except OSError as exc:
        logger.warning("Could not update the startup registry value: %s", exc)
        return False
    except Exception as exc:
        logger.exception("Unexpected startup registry error: %s", exc)
        return False
