#!/usr/bin/env python3
"""Build and bundle modular JavaScript files into web/app.js.

Maintains clean modular single-responsibility source files under web/js/
while producing the distribution IIFE bundle web/app.js for WebView2 runtime.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
JS_DIR = WEB_DIR / "js"
BUNDLE_PATH = WEB_DIR / "app.js"

MODULE_ORDER = [
    # Core
    "core/constants.js",
    "core/state.js",
    "core/dom.js",
    "core/utils.js",
    "core/api.js",
    "core/theme.js",
    # Playback
    "playback/clock.js",
    # Lyrics core
    "lyrics/sync.js",
    "lyrics/sweep.js",
    # UI components
    "ui/toasts.js",
    # Lyric rendering
    "lyrics/render-lyrics.js",
    "lyrics/render-mini.js",
    # IPC events from Python backend
    "ipc/track-events.js",
    "ipc/playback-events.js",
    # Lyrics features
    "playback/offset.js",
    "lyrics/export.js",
    "lyrics/lookup.js",
    "playback/timer.js",
    # Modals & Dialogs
    "modals/history-modal.js",
    "modals/vocab-modal.js",
    "modals/search-modal.js",
    "modals/cache-ops.js",
    "lyrics/context-menu.js",
    "modals/palette-modal.js",
    "modals/select-control.js",
    "modals/settings-actions.js",
    # Window modes
    "modes/mini-mode.js",
    "modes/square-mode.js",
    "modes/fullscreen-mode.js",
    # Settings & Overflow UI
    "modals/settings-sheet.js",
    "ui/overflow-menu.js",
    "ui/startup.js",
    "ui/apply-settings.js",
    "ui/tooltip.js",
    # Interaction wiring
    "ui/button-actions.js",
    "ui/scrubber.js",
    "ui/shortcuts.js",
    # Bootstrap / Init
    "bootstrap.js",
]


def bundle(check_only: bool = False) -> bool:
    """Concatenate modular JS files into web/app.js."""
    parts = [
        "/* ============================================================================\n",
        "   Spotify Realtime Lyrics - application state, rendering and IPC\n",
        "   Modular source files live under web/js/ - DO NOT EDIT MANUALLY\n",
        "   ========================================================================== */\n",
        "(function () {\n",
        "  'use strict';\n\n",
    ]

    for rel_path in MODULE_ORDER:
        file_path = JS_DIR / rel_path
        if not file_path.is_file():
            print(f"Error: missing module file: {file_path}", file=sys.stderr)
            return False
        content = file_path.read_text(encoding="utf-8")
        parts.append(content)
        if not content.endswith("\n"):
            parts.append("\n")

    parts.append("})();\n")
    bundled_text = "".join(parts)

    if check_only:
        if not BUNDLE_PATH.is_file():
            print("Error: web/app.js does not exist", file=sys.stderr)
            return False
        existing = BUNDLE_PATH.read_text(encoding="utf-8")
        if existing != bundled_text:
            print("Error: web/app.js is out of sync with web/js/ modules", file=sys.stderr)
            return False
        print("OK: web/app.js matches web/js/ modules")
        return True

    BUNDLE_PATH.write_text(bundled_text, encoding="utf-8")
    print(f"Successfully bundled {len(MODULE_ORDER)} modules into {BUNDLE_PATH}")
    return True


if __name__ == "__main__":
    check = "--check" in sys.argv
    success = bundle(check_only=check)
    sys.exit(0 if success else 1)
