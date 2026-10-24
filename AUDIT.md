# Project Audit — Spotify Lyrics & Translation (v2.5)

> Scope: whole repository (`main.py`, `media_listener.py`, `lyrics_service.py`,
> `translator_service.py`, `cache_service.py`, `romanizer.py`, `discord_rpc.py`,
> `web/*`, build/packaging). Focus: what is missing, why the UI feels dated
> ("2018"), and a memory-friendly modernization + feature roadmap.

---

## 1. Snapshot

- **Type:** Windows desktop companion for Spotify (frameless pywebview window).
- **Backend:** Python 3 + `winsdk` (GSMTC) + SQLite (WAL) + LRCLib + Google Translate (unofficial).
- **Frontend:** Vanilla HTML/CSS/JS, glassmorphism, 3 display modes (window / mini island / fullscreen).
- **Strengths:** Real local playback sync, offline cache, romanization, translation streaming, export (LRC/SRT/HTML), vocab notebook, Discord RPC, global hotkeys.
- **Packaging:** Single PyInstaller `--onefile --windowed` exe (~tens of MB), no installer, no auto-update, no tray.

---

## 2. Why it feels "2018"

### 2.1 Visual language (glassmorphism + neon)
- `web/style.css`: `backdrop-filter: blur(40px) saturate(200%)`, three animated `filter: blur(90px)` orbs, glowing `text-shadow`, `box-shadow` glows. This was the 2018–2020 "frosted neon" look. Modern desktop apps (Fluent 2 / Material 3 / Liquid Glass) use **lower blur (12–20px), solid-ish panels, subtle elevation, and adaptive color**, not heavy neon.
- Only dark themes exist (`dynamic/oled/tokyo/cyberpunk/nord`). No light mode, no `prefers-color-scheme`, no high-contrast.
- Radius/spacing are ad-hoc (`20px`, `14px`, `8px` mixed) instead of a token scale.

### 2.2 Iconography
- Mixed **emoji** (`📋 📄 💾 🎬 🖨️ 🕒 📚 🌙 ⭐ 🔊`) inside buttons and toasts. Emoji render inconsistently across Windows versions and read as "old app" UI.
- Inline SVGs use mixed stroke widths (2.2 / 2.5 / 1.5) and sizes (12–22px). No single icon set.
- **Fix:** adopt one consistent line-icon set (Lucide/Phosphor, 24×24, stroke 1.5) as an SVG sprite; remove all emoji from chrome (keep emoji only for language flags, or replace flags with code labels).

### 2.3 Interaction patterns
- Settings are a long checkbox list in a floating drawer; modern apps group into cards/sections with toggles and segmented controls.
- Toast is top-center and blocks; modern placement is bottom-right with queue.
- Modals are simple overlays with no focus trap / ESC handling parity (ESC closes some, not all).
- No onboarding, empty-state illustrations beyond a music note, no skeleton loading.
- Frameless window has `easy_drag` but no visible resize affordance; min size 360×85 is extreme.

### 2.4 Typography & assets
- Loads 4 Google Font families (`Plus Jakarta Sans` + 3 Noto) synchronously in `<head>` → render-blocking, heavy. No `font-display: swap`, no subsetting.
- Uses px-based sizes; no fluid type or tabular numerals for timers.

### 2.5 Tech choices that age the app
- No tests, no lint/type hints, no CI.
- `innerHTML` with song titles/thumbnails → XSS risk.
- Unofficial Google Translate endpoint (fragile, ToS).
- Single monolithic `app.js` (~1350 lines) with global state.

---

## 3. Memory & Performance Audit

| # | Finding | Location | Impact | Recommendation |
|---|---------|----------|--------|----------------|
| M1 | Two `CacheService()` instances (Lyrics + Translator) → two SQLite connections + WAL | `lyrics_service.py`, `translator_service.py` | Extra memory/handles | Share one instance via dependency injection |
| M2 | `artist_trans_cache` unbounded dict | `lyrics_service.py` | Slow growth | `functools.lru_cache(maxsize=256)` |
| M3 | Thumbnails up to 2.5MB base64 stored in SQLite (`song_history.thumbnail`) and pushed over IPC | `media_listener.py` (2.5MB cap), `cache_service.py` | Large DB + IPC spikes | Downscale to 96×96 JPEG q70 before store; store only hash+path |
| M4 | No lyrics list virtualization; long songs render hundreds of nodes | `app.js` `updateLyrics` | DOM/memory bloat | `content-visibility: auto` + IntersectionObserver windowing |
| M5 | Orb animations + `blur(90px)` always on, even background | `style.css` | GPU/CPU waste | Pause when `document.hidden` / reduced-motion / low battery |
| M6 | `evaluate_js` with huge JSON payloads (lyrics + translations) | `main.py` | IPC memory spikes | Chunk/stream (already streams translations); cap line count |
| M7 | No fetch cancellation on track change; `_fetch_and_translate_lyrics` can overlap | `main.py` (only `is_fetching` bool) | Wasted work/memory | Use `threading.Event` cancel token + ignore stale results |
| M8 | No cache eviction; DB grows unbounded | `cache_service.py` | Disk/memory over time | LRU by `updated_at`/`played_at` (cap: 500 lyrics, 5000 translations, 200 history) |
| M9 | Fonts render-blocking | `index.html` | Startup memory/CPU | `font-display: swap`, async load, subset to used glyphs |
| M10 | Color extraction runs on every artwork load with 32×32 canvas | `app.js` | Minor | Debounce + cache by thumbnail hash |
| M11 | `get_translations_batch` builds `IN (...)` with all texts (SQLite param limit ~999) | `cache_service.py` | Crash on long songs | Chunk to 500 |
| M12 | `winsdk` session enumeration every 1.2s even when idle | `media_listener.py` | CPU | Back off to 3s when no Spotify session |

**Memory-friendly target:** keep steady-state RSS under ~120MB and DB under ~25MB for typical use.

---

## 4. Functional Gaps (necessary features)

1. **Reliability:** no retry/backoff for LRCLib/Translate; no offline indicator; no "lyrics not found → manual search".
2. **Persistence:** only theme is saved; opacity, nudge offset, view mode, ghost, discord, sweep, romaji, learner flags are lost on restart.
3. **Windowing:** no system tray; closing quits; no auto-start; no multi-monitor/DPI handling.
4. **Accessibility:** no focus rings, ARIA, keyboard navigation of lyrics, reduced-motion support.
5. **Multi-source:** only Spotify desktop; Windows GSMTC already exposes Apple Music/YouTube/browser — not used.
6. **Cache management:** no view/clear cache, no size display.
7. **Updates:** no auto-update or "new version" notice.
8. **Security/privacy:** unofficial Translate; no opt-in telemetry/crash reporting; exports only to Desktop (no folder picker).

---

## 5. Competitive Landscape (GitHub)

| Project | What to borrow |
|---------|----------------|
| `Yudaotor/lyrimuse` | Multi-source (Apple/YouTube/QQ/NetEase), word-level timing, Last.fm scrobbling, notch/Dynamic Island |
| `EazyHood/Lyrio` | AI sync with true word timestamps, Shazam-style recognition, phone companion (QR), dual overlay, party mode, community sync upload |
| `afeibukaixin/Lyrics-Plus` | Word-level timing, local lyrics library, multi-provider search |
| `Diwasdh/Desktop-Lyrics` | Top Dynamic Island, kinetic canvas, click-through ghost mode, multi-player |
| `ateymoori/lyricglow` | RTL support, 43 languages, artist metadata, word-by-word karaoke |
| `iammrwrath/AuraMusic-Desktop` | Vocal isolation/karaoke, OBS streaming suite |
| `malemalice/floating-lyrics` | Menu bar + Touch Bar integration (macOS parity idea) |
| `Komortes/TrackPeek` | Notch/menu bar/desktop widgets |

---

## 6. Proposed New Features (20)

Priorities: **P0** (ship next), **P1** (soon), **P2** (later).

1. **P0 — System tray + quick actions + auto-start** (hide-to-tray, resume last mode, launch on login).
2. **P0 — Persist all settings** to `%APPDATA%/SpotifyLyrics/settings.json` with import/export.
3. **P0 — Per-song sync offset memory** (remember nudge per track; auto-apply).
4. **P0 — Lyrics provider fallback chain** (LRCLib → Genius → Musixmatch → manual) with confidence score.
5. **P0 — Manual lyrics search & correction editor** (search by title/artist, edit timestamps, save to cache).
6. **P1 — Word-level (syllable) timing** when source provides it; sweep follows actual singer.
7. **P1 — Multi-source playback** (any GSMTC app) with source picker & icon.
8. **P1 — Translation provider choice** (Google / DeepL / LibreTranslate / local Ollama) + offline cache-first.
9. **P1 — RTL + CJK typography** (proper `dir=rtl`, Arabic shaping, Noto variants lazy-loaded).
10. **P1 — Anki/JSON/CSV export** with spaced-repetition fields (word, reading, meaning, audio, song).
11. **P1 — Practice mode** (A–B repeat, speed 0.5–1.5×, line loop, hide translation toggle).
12. **P1 — Auto-update via GitHub Releases** (silent check, changelog, rollback).
13. **P1 — Accessibility pass** (focus rings, ARIA, keyboard lyric nav, reduced-motion, high-contrast theme).
14. **P1 — Light mode + adaptive Fluent theming** (Mica/Acrylic, system accent color).
15. **P2 — Cache manager UI** (size, entries, clear by type, export DB).
16. **P2 — Community sync upload** to LRCLib with credit.
17. **P2 — Phone companion** (QR → local web view of current lyrics, same Wi-Fi).
18. **P2 — OBS/overlay mode** (transparent chroma window, scene-friendly).
19. **P2 — Last.fm scrobbling** + listening stats (top songs, streaks).
20. **P2 — Plugin API** (JS hooks for custom renderers/themes).

---

## 7. Modernization Roadmap

### Phase A — Quick wins (1–2 days)
- Replace emoji with Lucide icons; remove neon glows; reduce blur to 16–24px.
- Persist settings; add light mode + `prefers-color-scheme`.
- Add `font-display: swap` and async font loading.
- Fix XSS (`textContent`), chunk SQLite `IN`, guard param limits.
- Pause animations when hidden; reduced-motion media query.

### Phase B — Memory & reliability (3–5 days)
- Share `CacheService`; LRU caches; thumbnail downscaling; cache eviction.
- Cancel tokens for fetch/translate; retry with exponential backoff.
- Virtualize lyrics list; `content-visibility: auto`.
- Tray + auto-start + close-to-tray.

### Phase C — Features (1–3 weeks)
- Provider fallback + manual search/editor.
- Word-level timing + practice mode.
- Multi-source + translation provider choice.
- Auto-update + cache manager.

### Phase D — Platform polish (ongoing)
- Accessibility audit, i18n of UI, plugin API, phone companion, OBS mode.

---

## 8. Quick Wins Checklist (copy into issues)

- [ ] `web/index.html`: load fonts with `display=swap` and `media="print" onload` trick.
- [ ] `web/style.css`: add `@media (prefers-reduced-motion: reduce)` to disable orb/spin/equalize.
- [ ] `web/app.js`: replace emoji buttons with SVG icons; use `textContent` for history rows.
- [ ] `main.py`: persist settings via `AppAPI`; add `get_settings`/`set_setting`.
- [ ] `lyrics_service.py`: share cache instance; `lru_cache` artist translation.
- [ ] `media_listener.py`: downscale thumbnail to 96×96 before base64; back off polling when idle.
- [ ] `cache_service.py`: add eviction + chunked `IN`.
- [ ] Add `docs/ARCHITECTURE.md` and a smoke test for cache + lrc parser.

---

## 9. Risks

- **Unofficial Translate** may break or be blocked; keep cache-first and allow provider swap.
- **PyInstaller one-file** cold start + AV false positives; consider code signing + installer (Inno Setup) + onefolder for faster start.
- **No tests** means regressions likely during refactor; add at least parser/cache unit tests before Phase B.

---

*Generated from repository audit on 2026-10-24.*
