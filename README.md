# 🎵 Spotify Lyrics & Real-Time Translation (v2.5)

A standalone desktop companion for Spotify with modern glassmorphism, instant synchronization, bilingual translation (Japanese, Korean, Spanish, French, German, Arabic, Hindi, etc.), and interactive playback controls.

---

## 🚀 How to Use

1. Double-click **`SpotifyLyrics.exe`** (no installation, Python, or admin rights required).
2. Play any song on **Spotify**.
3. Real-time karaoke lyrics and **English translations** will appear and scroll in sync!

---

## ✨ Features & UI Modes

### 1. 🔲 Three Display Modes
- **Window Card Mode (Default):**
  - Apple Music Sing-inspired typography with blurred unfocused lines and crisp highlighted active lines.
  - Interactive bottom dock with live progress scrubber and media controls (Play/Pause, Previous, Next).
  - Click any lyric line to jump Spotify directly to that part of the song!
- **Floating Dynamic Island Pill (Mini Mode):**
  - Click the **Mini** button in the header (or drag anywhere).
  - Transforms into a floating rounded capsule showing the spinning vinyl disc, current original line, and glowing English subtitle.
  - Hover reveals quick controls (Play/Pause, Next, Pin, Expand).
- **Fullscreen Immersive Mode:**
  - Click the **Fullscreen** button or press **F11** (press **Esc** or F11 to exit).
  - Ambient fluid gradient mesh with centered cinematic lyrics.

### 2. ⚡ Seeking & Instant Sync
- **Native Windows Media Integration (`winsdk`):** Direct kernel communication with Spotify's timeline — zero PowerShell overhead.
- **Event-Driven Seeking:** Seeks in Spotify now immediately snap the lyrics to the exact timestamp without getting stuck.
- **Interactive Scrubber:** Click or drag on the progress bar in the app to scrub through the song.

### 3. 🌐 Intelligent Language & Bilingual Resolvers
- Automatically detects bilingual titles like `괴도 (Danger)` or `봄날 (Spring Day)` and matches synced lyrics.
- Translates Hangul artist names (e.g., `방탄소년단` → `BTS`) to match global lyric databases.
- Fast multi-line background translation streaming with zero playback interruption.

---

## 🛠 Rebuilding

To rebuild the single executable after making changes:
```bash
python build.py
```
Outputs to `SpotifyLyrics.exe`.
