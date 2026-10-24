# 🎵 Spotify Lyrics & Real-Time Translation (v3.0)

A high-performance, lyrics-first desktop companion for Spotify on Windows. Features synchronized karaoke streaming, multi-provider lyric sourcing (Local `.lrc`, LRCLIB, NetEase), automatic translation and romanization (Romaji, Romaja, Pinyin), single-instance guard, system tray integration, and custom 2026 UI controls.

---

## 🚀 Quick Start

### Run the Standalone Binary
1. Download or locate **`SpotifyLyrics.exe`**.
2. Run `SpotifyLyrics.exe` (no Python or installation required).
3. Play any track in **Spotify for Windows**.
4. Lyrics, romanizations, and translations will synchronize and scroll automatically!

### Run from Source
Requires Python 3.12+ on Windows 10/11:
```powershell
# Install runtime dependencies
pip install -r requirements.txt

# Launch the app
python main.py
```

### Build Single Executable
```powershell
pip install -r requirements-dev.txt
python build.py
```
Produces an optimized ~24 MB standalone executable at `dist/SpotifyLyrics.exe` and copies it to the workspace root.

---

## 🆕 What's New in v3.0

- **Data Persistence & Isolation:**
  - Database and caches are stored permanently in `%LOCALAPPDATA%\SpotifyLyrics\spotify_lyrics.db` (never inside temporary PyInstaller folders).
  - Logs are written cleanly to `%LOCALAPPDATA%\SpotifyLyrics\logs\app.log`.
  - **Portable Mode:** Create an empty `portable.flag` file beside `SpotifyLyrics.exe` to redirect all databases, settings, and logs to `./data/`.
- **Multi-Provider Lyrics Engine:**
  - **Local `.lrc`:** Save, edit, and read local `.lrc` files from `%LOCALAPPDATA%\SpotifyLyrics\lrc\`. Local files always take precedence over remote network caches.
  - **LRCLIB:** Primary global provider for synced and unsynced international lyrics.
  - **NetEase Cloud Music:** Secondary provider with rich Asian/C-pop coverage and native translation merging.
  - **Manual Lyrics Search:** Search across all providers, inspect match scores, and switch candidates on the fly.
- **Windows Integration:**
  - **Single Instance Guard:** Named Windows mutex (`Local\SpotifyLyrics_v3`) prevents duplicate processes and brings the existing window to the foreground.
  - **Native System Tray:** Lightweight ctypes-based tray icon with Show/Hide, Play/Pause, Mini mode, Settings, and Quit. Survives Windows Explorer restarts.
  - **Close-to-Tray:** Closing the window hides it cleanly to the system notification area without stopping playback tracking.
  - **Window State Persistence:** Remembers window position (X, Y), dimensions (Width, Height), pin state, and view mode across restarts.
  - **Start with Windows:** Easily toggle automatic boot launch via registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).
- **2026 Modern Visual Redesign:**
  - 100% SVG icon sprite system (zero emoji glyphs).
  - Custom accessible controls: iOS-style switch toggles, custom sliders, segmented pills, and custom dropdown menus.
  - Clean system typography stack (`Plus Jakarta Sans`, `Segoe UI Variable`, `Segoe UI`, `Malgun Gothic`, `Yu Gothic UI`, `Microsoft YaHei UI`).
  - Dark, OLED, Light, and System theme modes with dynamic album-accent highlights.
  - Ultra-low CPU/RAM usage (~35 MB RAM, native 60–144 FPS client-side smooth animation loop).
- **Command Palette (Ctrl+K):**
  - Instant fuzzy search across settings, themes, view modes, song history, saved vocabulary, and export actions.
- **Study & Utility Tools:**
  - **Vocabulary Notebook:** Double-click any foreign word to inspect definitions and phonetic romanization, and star words to export a CSV vocabulary deck.
  - **Offline Exports:** Export synchronized `.lrc` files, `.srt` subtitle tracks, or printable poster-style HTML lyric sheets to your Desktop.
  - **Sleep Timer:** Automatic Spotify playback pause countdown.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action | Scope |
|---|---|---|
| <kbd>Ctrl</kbd> + <kbd>K</kbd> | Open / Close Command Palette | In-app |
| <kbd>F11</kbd> | Toggle Immersive Fullscreen | In-app |
| <kbd>Esc</kbd> | Close Fullscreen / Modals / Palette | In-app |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>G</kbd> | Toggle Gamer Ghost Mode (Click-Through) | Global (System-wide) |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>M</kbd> | Toggle Mini Island Bar Overlay | Global (System-wide) |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>H</kbd> | Boss Key (Instant Hide / Show) | Global (System-wide) |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>L</kbd> | Cycle Lyric View Mode (Dual / Trans / Orig) | Global (System-wide) |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Space</kbd> | Play / Pause Spotify | Global (System-wide) |

---

## 🔒 Privacy & Translation Notes

- **No Account Required:** The app communicates directly with Windows System Media Transport Controls (SMTC) to read the currently playing track. No Spotify developer API tokens or login credentials are required.
- **Translation Provider:** Multi-line translations and dictionary definitions query Google Translate endpoints over HTTPS without transmitting telemetry or user identities.
- **Local Storage:** All history, vocabulary, and lyric caches reside locally on your PC in SQLite. No tracking or analytics servers are contacted.

---

## 🔧 Troubleshooting

1. **"Waiting for Spotify...":**
   - Ensure the Spotify desktop app is open and currently playing a song.
   - If Spotify was recently installed from the Microsoft Store, restart Spotify once to register Windows SMTC media transport controls.
2. **Missing WebView2 Runtime:**
   - On Windows 10/11, WebView2 is typically preinstalled. If a missing runtime error appears, install the [Microsoft Edge WebView2 Evergreen Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).
3. **Application Logs:**
   - Detailed debug logs are written to `%LOCALAPPDATA%\SpotifyLyrics\logs\app.log` (or `<install_dir>\data\logs\app.log` in portable mode).
