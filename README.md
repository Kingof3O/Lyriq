<p align="center">
  <img src="Lyriq_Brand_Assets/04_Banners/hero-banner-16x9.png" alt="Lyriq Banner" width="100%" style="border-radius: 12px; box-shadow: 0 12px 36px rgba(0,0,0,0.5);">
</p>

<h1 align="center">Lyriq (v3.0)</h1>

<p align="center">
  <strong>A high-performance, lyrics-first desktop instrument for Spotify on Windows.</strong><br>
  Real-time synchronized karaoke typography, multi-line translation, phonetic romanization (Romaji / Pinyin / Romaja), and zero-distraction desktop presentation modes.
</p>

<p align="center">
  <a href="https://github.com/Kingof3O/Lyriq/releases/latest"><img src="https://img.shields.io/github/v/release/Kingof3O/Lyriq?color=8B5CF6&label=Release&logo=github&style=flat-square" alt="Latest Release"></a>
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(64--bit)-0078D6?logo=windows&style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/Runtime-Microsoft%20Edge%20WebView2-0078D7?logo=microsoftedge&style=flat-square" alt="Edge WebView2">
  <img src="https://img.shields.io/badge/Discord%20RPC-Supported-5865F2?logo=discord&style=flat-square" alt="Discord RPC">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-10B981?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="#-quick-start--downloads"><strong>⬇️ Downloads</strong></a> •
  <a href="#-product-philosophy"><strong>💡 Philosophy</strong></a> •
  <a href="#-presentation-modes"><strong>🖥️ Presentation Modes</strong></a> •
  <a href="#-features"><strong>✨ Key Features</strong></a> •
  <a href="#️-keyboard-shortcuts"><strong>⌨️ Shortcuts</strong></a> •
  <a href="#-architecture"><strong>🛠️ Architecture</strong></a> •
  <a href="#-development--building"><strong>📦 Building</strong></a>
</p>

---

## ⚡ Quick Start & Downloads

### Download Standalone Binary (No Installation Required)

Lyriq is packaged as a standalone 64-bit Windows executable. **You do not need Python, Node.js, or any developer tools to run it.**

| Package | Format | Description | Download |
|---|---|---|---|
| **Lyriq Portable Zip** | `.zip` (~40 MB) | Complete package with `Lyriq.exe` and quick start documentation | [**Download .zip**](https://github.com/Kingof3O/Lyriq/releases/latest/download/Lyriq-v3.0-Windows.zip) |
| **Lyriq Standalone EXE** | `.exe` (~40 MB) | Single-file binary. Put it anywhere and double-click to run | [**Download .exe**](https://github.com/Kingof3O/Lyriq/releases/latest/download/Lyriq.exe) |

1. Download **`Lyriq-v3.0-Windows.zip`** (or `Lyriq.exe`).
2. Run **`Lyriq.exe`**.
3. Open **Spotify for Windows** and play any track.
4. Synchronized lyrics, translations, and romanizations stream automatically!

---

## 💡 Product Philosophy

> **LYRICS FIRST → CONTROLS SECOND → APPLICATION CHROME THIRD**

Lyriq is designed specifically as a **desktop lyrics instrument**, not a Spotify replacement.

- **Spotify owns**: Library management, audio streaming, playlist curation, discovery algorithms.
- **Lyriq owns**: Synchronized typography, sub-millisecond karaoke timing, multi-line translation, phonetic romanization, provider fallback matching, vocabulary study, and immersive presentation modes.

The lyrics stage is the product. There are **no permanent left navigation sidebars**, no generic SaaS cards, no intrusive ads, and no global window scroll jitter.

---

## 📸 Visual Showcase

### Primary Reader Mode
<p align="center">
  <img src="docs/audit/v3/00_reader_desktop_1120x760.png" alt="Lyriq Reader Mode" width="100%" style="border-radius: 8px;">
</p>

*Clean synchronized typography with 3px violet active rail, dynamic ambient album atmosphere, and a full-width edge-to-edge media player dock.*

---

## 🖥️ Presentation Modes

Lyriq adapts to whatever you are doing on your PC with five dedicated presentation modes:

| Mode | Shortcut | Preview | Description |
|---|---|---|---|
| **Reader Mode** | Default | <img src="docs/audit/v3/01_card_synced.png" width="220" alt="Reader"> | The canonical desktop lyrics instrument with smooth word-by-word active sweep, translation, and romanization. |
| **Fullscreen Split** | <kbd>F11</kbd> | <img src="docs/audit/v3/03_fullscreen_split.png" width="220" alt="Fullscreen"> | Immersive high-definition split stage: album artwork on the left, full synchronized lyric scroll on the right. |
| **Square Mode** | <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>S</kbd> | <img src="docs/audit/v3/10_square_mode.png" width="220" alt="Square"> | Compact vinyl album card view with integrated controls, ideal for secondary vertical or horizontal monitors. |
| **Mini Island** | <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>M</kbd> | <img src="docs/audit/v3/screenshots/06_mini_island.png" width="220" alt="Mini"> | Ultra-compact floating pill widget. Always on top, docked near your taskbar or corner with live lyric scroll. |
| **Gamer Ghost HUD** | <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>G</kbd> | <img src="docs/audit/v3/screenshots/09_ghost_hud.png" width="220" alt="Ghost"> | 100% click-through transparent HUD (`WS_EX_TRANSPARENT`). Play games or write code with lyrics floating on top. |

---

## ✨ Key Features

### 🎵 Multi-Provider Sync Engine
- **Local `.lrc` Priority**: Drop custom or edited `.lrc` files into `%LOCALAPPDATA%\SpotifyLyrics\lrc\` to immediately override remote sources.
- **LRCLIB**: Primary global crowd-sourced synced and unsynced lyrics catalog.
- **NetEase Cloud Music**: Secondary high-coverage Asian music provider with bilingual and native translated lyrics.
- **Manual Lyrics Search**: Search any song across all providers, inspect match similarity scores, and pick the best candidate on the fly (<kbd>Ctrl</kbd>+<kbd>K</kbd> → *Search lyrics*).

<p align="center">
  <img src="docs/audit/v3/07_manual_search.png" alt="Manual Lyrics Search" width="70%" style="border-radius: 8px;">
</p>

### 🌐 Real-Time Translation & Phonetic Romanization
- **3 Lyric Views**: Switch effortlessly between **DUAL** (Original + Translation), **TRANSLATION ONLY**, or **ORIGINAL ONLY**.
- **Asian Phonetic Romanization**:
  - **Japanese**: Hepburn Romaji conversion.
  - **Korean**: Revised Romanization (Romaja) transcription.
  - **Chinese**: Pinyin transcription with accurate syllable mapping.
- **RTL (Right-to-Left) Support**: Native bidirectional typography rendering for Arabic, Hebrew, and Persian lyrics.

<p align="center">
  <img src="docs/audit/v3/09_arabic_lyrics.png" alt="RTL Arabic Lyrics Support" width="70%" style="border-radius: 8px;">
</p>

### 🎓 Study Lens & Vocabulary Notebook
- Double-click any foreign word in the lyrics to instantly open the **Study Lens** sidebar.
- Inspect dictionary definitions, parts of speech, phonetic pronunciation, and contextual nuance notes.
- Star words to save them to your personal **Vocabulary Notebook** and export them to CSV study decks for Anki or Quizlet.

<p align="center">
  <img src="docs/audit/v3/screenshots/10_study_lens.png" alt="Study Lens" width="70%" style="border-radius: 8px;">
</p>

### 🎛️ Hardware-Level Volume Control & Media Dock
- **Direct Spotify Volume Control**: Direct Windows Core Audio (WASAPI) session control — adjusting the slider modifies Spotify's volume directly without altering global Windows system sounds.
- **Mouse Wheel Gesture**: Simply scroll your mouse wheel over the album artwork or the player dock to raise or lower the volume.
- **Full-Width Integrated Scrubber**: 3px hairline scrubber spanning edge-to-edge along the top rim of the dock, expanding to 5px with illuminated handle on hover.

### 🎧 Discord Rich Presence
- Broadcasts the currently playing song title, artist name, elapsed track timestamps, and official Lyriq brand artwork directly to your Discord profile.
- Built-in IPC pipe connector with customizable Application ID support in Settings.

### ⚡ Command Palette (<kbd>Ctrl</kbd> + <kbd>K</kbd>)
- Quick launcher for everything: cycle themes, toggle presentation modes, search lyrics, inspect song playback history, manage saved vocabulary, and export `.lrc` / `.srt` / HTML lyric sheets.

<p align="center">
  <img src="docs/audit/v3/05_command_palette.png" alt="Command Palette" width="70%" style="border-radius: 8px;">
</p>

### 💾 Data Persistence & Portable Mode
- **Persistent Local Database**: Caches, settings, song history, and vocabulary are saved permanently in `%LOCALAPPDATA%\SpotifyLyrics\spotify_lyrics.db` with SQLite Write-Ahead Logging (WAL).
- **Portable Mode**: Place an empty `portable.flag` file beside `Lyriq.exe`. All databases, settings, and logs will be isolated to `./data/` on your USB flash drive.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action | Scope |
|---|---|---|
| <kbd>Ctrl</kbd> + <kbd>K</kbd> | Open / Close Command Palette | In-app |
| <kbd>F11</kbd> | Toggle Fullscreen Split Stage | In-app |
| <kbd>Esc</kbd> | Close Fullscreen / Modals / Palette / Study Lens | In-app |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>G</kbd> | Toggle Gamer Ghost HUD (Click-Through) | Global (System-wide) |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>M</kbd> | Toggle Mini Island Overlay Bar | Global (System-wide) |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | Toggle Square Album Card Mode | Global (System-wide) |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>H</kbd> | Boss Key (Instant Hide / Show to Tray) | Global (System-wide) |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>L</kbd> | Cycle Lyric View Mode (Dual / Trans / Orig) | Global (System-wide) |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Space</kbd> | Play / Pause Spotify | Global (System-wide) |

---

## 🛠️ Architecture

```mermaid
flowchart TD
    Spotify["Spotify for Windows"] -->|Windows SMTC| MediaListener["MediaListener (WinRT / winsdk)"]
    MediaListener -->|Track Change & Timeline| MainApp["SpotifyLyricsApp (Python 3.12 Host)"]
    
    MainApp --> Pipeline["Multi-Provider Lyrics Pipeline"]
    Pipeline --> LocalProvider["Local .lrc Provider"]
    Pipeline --> LrcLibProvider["LRCLIB Provider"]
    Pipeline --> NetEaseProvider["NetEase Provider"]
    
    Pipeline --> Romanizer["Romanizer Engine (Romaji / Pinyin / Romaja)"]
    Pipeline --> Translator["Translator Service (Google API / Stream)"]
    
    Romanizer --> Cache["SQLite Cache (WAL Mode)"]
    Translator --> Cache
    
    MainApp --> Win32Native["Win32 Native Controller (Styles / Topmost / Click-Through)"]
    MainApp --> PycawControl["Core Audio WASAPI (pycaw Volume)"]
    MainApp --> DiscordRPC["Discord IPC (Rich Presence)"]
    
    MainApp <-->|Two-Way JS API Bridge| WebView2["Microsoft Edge WebView2 (WinForms)"]
    WebView2 --> WebFrontend["Vanilla ES6 Frontend (Zero Frameworks, 60-144 FPS)"]
```

---

## 📦 Development & Building

### Running from Source
Requires **Python 3.12+** on Windows 10 or 11:

```powershell
# Clone the repository
git clone https://github.com/Kingof3O/Lyriq.git
cd Lyriq

# Install dependencies
pip install -r requirements.txt

# Run developer test suite (112 unit tests)
python -m unittest discover -s tests

# Launch application
python main.py
```

### Compiling Standalone Executable
```powershell
# Install build tools
pip install -r requirements-dev.txt

# Compile standalone Lyriq.exe
python build.py
```
The build script bundles the modular ES6 frontend, generates the multi-resolution `.ico`, runs PyInstaller, and produces an optimized standalone executable at `Lyriq.exe`.

---

## 🔒 Privacy & Local Storage

- **No Account Required**: Lyriq reads the Windows System Media Transport Controls (SMTC) broadcast emitted by the Spotify desktop client. No Spotify account credentials or developer tokens are needed.
- **Zero Telemetry**: Lyriq contains zero trackers, analytics, or background telemetry.
- **Local Storage**: All history, saved vocabulary, lyrics caches, and configuration settings remain stored locally on your device in SQLite.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Developed with ❤️ by [Kingof3O](https://github.com/Kingof3O).
