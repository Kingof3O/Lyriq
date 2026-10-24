# 🔍 Project Audit: Spotify Lyrics & Real-Time Translation (v2.5)

**Date:** October 2026  
**Project:** Standalone Windows desktop companion for Spotify  
**Stack:** Python + pywebview (Edge WebView2) + SQLite + vanilla HTML/CSS/JS

---

## 1. Executive Summary

This is a genuinely solid, feature-rich lyrics companion app with several strengths:
- **Native Windows media integration** via `winsdk` (SMTC) — zero PowerShell overhead, event-driven seeking
- **Bilingual lyrics** with original + translation + romanization (Korean/Japanese/Chinese)
- **Three display modes**: Window Card, Floating Dynamic Island, Fullscreen Immersive
- **Offline caching** (SQLite) for lyrics, translations, song history, favorites, vocab notebook
- **Discord Rich Presence**, sleep timer, ghost mode, boss key, global hotkeys
- **Exports**: .LRC, .SRT, printable HTML lyric poster

However, the **UI/UX and visual design feel dated (2018–2020 era)**, the **frontend is raw vanilla JS without a build step**, icons are hand-written SVG paths, and there are **memory/architecture concerns** for long-running sessions.

---

## 2. What Feels "2018 Style" & Why

| Area | Current State | Why It Feels Dated | Modern Equivalent |
|------|--------------|-------------------|-------------------|
| **Icons** | Hand-written inline SVG `<path>` strings scattered in HTML | No icon system, monochrome strokes only, hard to maintain, no filled/outline variants | Lucide / Phosphor / Heroicons icon library with consistent 24px grid |
| **CSS Architecture** | ~1,500 lines of custom CSS in one file, CSS variables used but no design system | No spacing scale, no typography scale, no component primitives | Tailwind CSS or a design-token system with consistent spacing/typography |
| **Frontend Build** | Raw HTML/CSS/JS, no bundler, no transpiler, no TypeScript | 2010s "edit file and refresh" workflow, no minification, no tree-shaking | Vite / esbuild + TypeScript for type safety and smaller bundle |
| **UI Framework** | Vanilla DOM manipulation, global state variables, inline event listeners | jQuery-era patterns, hard to scale, no reactivity | Preact / React / Svelte or at least a lightweight reactive system |
| **Form Controls** | Native `<select>`, `<input type=range>`, `<input type=checkbox>` | OS-styled, inconsistent across Windows versions, no custom states | Custom-styled buttons, toggles, sliders with focus states |
| **Glassmorphism** | `backdrop-filter: blur(40px) saturate(200%)` everywhere | Overused 2020 trend; heavy GPU cost, reduces readability, looks "template-y" | Subtle frosted glass with borders, used sparingly; solid surfaces for text |
| **Animations** | CSS `@keyframes` only (floatOrb, spinDisc, radar) | Basic looping animations, no enter/exit transitions, no staggered lists | Framer Motion / CSS transitions with `will-change`, reduced-motion support |
| **Responsiveness** | Fixed 480×720 window, no scaling | Doesn't adapt to HiDPI, window resizing breaks layout | Fluid layout, min/max constraints, HiDPI-aware |
| **Accessibility** | No ARIA labels, no keyboard nav, no focus traps, no reduced-motion | Inaccessible to screen readers, keyboard-only users | ARIA roles, keyboard shortcuts visible, `prefers-reduced-motion` |
| **Loading States** | None — content just appears or shows "Connecting..." | Feels unfinished, no feedback during fetch | Skeleton screens, spinner pills, optimistic UI |
| **Theme System** | 4 hardcoded themes via `data-theme` | No user color picker, no accent customization, no dynamic wallpaper sync | CSS color-scheme + user-defined accent color, wallpaper color extraction |
| **Typography** | Plus Jakarta Sans + Noto Sans CJK via Google Fonts | Two weights of CJK loaded (blocking), no font-display optimization | `font-display: swap`, subset CJK fonts, system font fallbacks |

### Specific Visual "Smells"
1. **Inline SVG icon paths** — ~15 different hand-written paths in `index.html`. Hard to read, impossible to theme (stroke vs fill), no icon consistency.
2. **Heavy glass backdrop** — `blur(40px) saturate(200%)` on the entire app background makes text harder to read and burns GPU.
3. **No skeleton/loading UI** — lyrics just pop in; translation streaming has no indicator.
4. **Native form controls** — `<select>` dropdowns look like Windows 7/10, not modern.
5. **Scrollbar styling** is basic `-webkit-scrollbar` only.
6. **Toast pill** is the only modern-feeling notification component.
7. **No empty-state illustrations** — just text + SVG radar icon.

---

## 3. Code & Architecture Review

### Python Backend (`main.py`, `lyrics_service.py`, `cache_service.py`, `translator_service.py`, `media_listener.py`, `discord_rpc.py`)

**Strengths:**
- Clean separation of concerns (media, lyrics, translation, cache, Discord)
- WAL mode on SQLite for concurrent reads
- Lyrics cached to disk — instant repeat lookup
- Translation batching with cache (35-text chunks)
- Artist name translation (Hangul → EN) for better LRCLib matching
- Bilingual title parsing (`괴도 (Danger)`)

**Concerns / Technical Debt:**
1. **Google Translate unofficial API** (`translate.googleapis.com/translate_a/single`) — no API key, rate-limited, could break anytime, no retry/backoff logic
2. **LRCLib as sole lyrics source** — no fallback (Genius, Musixmatch, Spotify's own lyrics)
3. **No LRU/TTL cache eviction** — `lyrics_cache.db` and `translation_cache` grow unbounded
4. **SQLite connection opened/closed per operation** — no connection pooling, overhead on every fetch
5. **Base64 thumbnails stored in memory + DB** — album art can be large; no size cap beyond 2.5MB
6. **`requestAnimationFrame` loop runs 60fps even when idle** — wasteful CPU when app is backgrounded
7. **No error boundaries** — if lyrics fetch fails, silent `return` with no user-facing retry (except manual button)
8. **Discord RPC uses a generic/hardcoded Client ID** — may not work reliably, no user-configurable app
9. **`pywebview` + Windows-only ctypes** — not cross-platform, Windows-only distribution
10. **No logging to file** — only `print()` / `logging.debug()`, hard to debug in production
11. **No config file** — all settings in-memory, lost on restart (except theme in localStorage)

### Frontend (`web/app.js`, `web/style.css`, `web/index.html`)

**Strengths:**
- Clean 3-mode architecture (window / island / fullscreen)
- Word-by-word karaoke sweep (CSS `background-clip: text` progress)
- Instrumental solo detection (gap > 6s)
- Sync nudge (±0.2s) — rare and useful feature
- Click-to-seek on lyric lines
- Double-click word lookup + TTS pronunciation
- Vocab notebook + song history + favorites

**Concerns:**
1. **~1,350 lines of vanilla JS in one file** — global state, no modules, hard to test
2. **Direct DOM manipulation everywhere** — no virtual DOM, easy to create bugs when adding features
3. **No TypeScript** — runtime errors only caught at execution
4. **No state management** — `activeIndex`, `currentLyrics`, `syncOffset` as loose globals
5. **No debounce/throttle** on scroll or media events
6. **`evaluate_js` string interpolation** — potential injection if track titles contain quotes (uses `json.dumps` so partially safe, but fragile)
7. **No service worker** — app can't work offline beyond cache
8. **Images not lazy-loaded** — album art fetched immediately

---

## 4. Memory & Performance Concerns

| Issue | Impact | Severity |
|-------|--------|----------|
| `pywebview` spawns Edge WebView2 | ~100–200MB baseline RAM just for the webview | High (unavoidable with this stack) |
| Continuous `requestAnimationFrame` loop | CPU wakeups even when idle/paused | Medium |
| Base64 album art in memory + SQLite | Each thumbnail ~100–500KB, cached forever | Medium |
| SQLite connections per query | No pooling, file I/O on every lyrics fetch | Low |
| Unbounded `lyrics_cache.db` | Grows with every new song played | Medium |
| Unbounded `translation_cache.db` | Grows with every translated line | Medium |
| Google Translate API calls per song | Network latency, rate limits, no offline fallback | High (UX, not memory) |
| 40px backdrop-filter blur | GPU compositing cost on every frame | Medium |

**Memory-friendly recommendations:**
1. Cap `lyrics_cache.db` and `translation_cache.db` (e.g., max 1,000 entries, LRU eviction)
2. Cap thumbnail cache (keep only current + last 5, delete old base64 from DB)
3. Pause `requestAnimationFrame` when `document.hidden` or app is minimized
4. Use `IntersectionObserver` to only render visible lyric lines (virtual scrolling for long songs)
5. Add `PRAGMA cache_size` and `PRAGMA temp_store = MEMORY` to SQLite
6. Compress thumbnails to JPEG quality 70 before base64 encoding

---

## 5. Feature Gap Analysis vs. Competitors

| Feature | Your App | Lyricify (7.3k★) | LyricsX (5.2k★) | Spotify Lyrics Translator | Verdict |
|---------|---------|------------------|-----------------|--------------------------|---------|
| Synced lyrics | ✅ LRCLib | ✅ Multiple sources | ✅ Multiple sources | ✅ Spotify Web Playback SDK | You match |
| Translation | ✅ Google Translate | ❌ | ❌ | ✅ | You lead |
| Romanization | ✅ Custom (KO/JA/ZH) | ❌ | ❌ | ✅ | You match |
| Multiple display modes | ✅ 3 modes | ✅ Many (desktop, menubar, mobile) | ✅ Desktop + menubar | ❌ Web only | You match |
| Song history + favorites | ✅ | ✅ | ✅ | ❌ | You match |
| Vocabulary notebook | ✅ | ❌ | ❌ | ❌ | **You lead** |
| Word lookup + TTS | ✅ | ❌ | ❌ | ❌ | **You lead** |
| Lyrics export (.lrc/.srt) | ✅ | ❌ | ✅ (LRCX import/export) | ❌ | You match |
| Cross-platform | ❌ Windows only | ✅ Windows + Mobile | ❌ macOS only | ✅ Web | **Gap** |
| Multiple lyrics sources | ❌ LRCLib only | ✅ Many | ✅ Many | ❌ Spotify only | **Gap** |
| Desktop lyrics (always-on-top overlay) | ❌ | ✅ | ✅ | ❌ | **Gap** |
| Menubar/tray app | ❌ | ❌ | ✅ | ❌ | **Gap** |
| Custom font / size | ❌ | ✅ | ✅ | ❌ | **Gap** |
| Lyrics offset/nudge | ✅ (±0.2s) | ✅ | ✅ | ❌ | You match |
| Auto-translate language detect | ✅ | ❌ | ❌ | ❌ | You lead |
| Sleep timer | ✅ | ❌ | ❌ | ❌ | **You lead** |
| Discord RPC | ✅ | ❌ | ❌ | ❌ | **You lead** |
| Ghost/click-through mode | ✅ | ❌ | ❌ | ❌ | **You lead** |
| Boss key | ✅ | ❌ | ❌ | ❌ | **You lead** |
| Offline cached lyrics | ✅ | ✅ | ✅ | ❌ | You match |
| Multiple music players (Apple Music, etc.) | ❌ Spotify only | ✅ Many | ✅ Many | ❌ Spotify only | **Gap** |

**Your unique advantages:** vocab notebook, word lookup+TTS, sleep timer, Discord RPC, ghost mode, boss key, translation+romanization combo. These are strong differentiators.

**Key gaps to close:** multiple lyrics sources, cross-platform support, tray/menubar mode, desktop overlay, custom typography, better icon system, modern UI.

---

## 6. 20 New Feature Suggestions (Prioritized)

### P0 — High Impact, Low Effort (Modern UI & UX)

1. **Modern Icon System (Lucide Feather icons)** — Replace hand-written SVG paths with a consistent icon library. Adds `lucide` via CDN or bundles icons as SVG sprites. Instantly modernizes the look.
   - *Why:* Icons are the most visible "dated" element; a consistent icon system makes the app feel professionally designed.

2. **Skeleton Loading States** — Show skeleton cards while lyrics/translation are fetching instead of empty/idle state.
   - *Why:* Perceived performance; app feels faster and more polished.

3. **Custom Font & Size Controls** — Let users choose font family (system, Plus Jakarta, etc.) and scale lyrics size (12px–24px).
   - *Why:* Accessibility + personalization; CJK users need larger glyphs.

4. **Accent Color Picker** — User-selectable accent color (Spotify green, cyan, purple, pink, etc.) applied to buttons, active line indicator, spectrum.
   - *Why:* Personalization makes the app feel premium.

5. **Reduced Motion Support** — Respect `prefers-reduced-motion`; disable floatOrb, spinDisc, toast slide when enabled.
   - *Why:* Accessibility requirement; vestibular users.

### P1 — High Value Features

6. **Multiple Lyrics Sources** — Add Genius, Musixmatch, or Spotify's own lyrics as fallback when LRCLib fails.
   - *Why:* LRCLib has gaps; coverage improves user retention.

7. **Desktop Lyrics Overlay (Always-on-top floating lyrics)** — A separate always-on-top transparent window showing just the current line, click-through, positionable anywhere on screen.
   - *Why:* Lyricify and LyricsX both have this; it's the #1 requested feature for desktop lyrics apps.

8. **System Tray / Menubar App** — Minimize to tray instead of taskbar; show current song + play/pause in tray tooltip; double-click tray to restore.
   - *Why:* Users want the app out of the way but accessible.

9. **Smart Cache Management (LRU + TTL)** — Auto-evict old lyrics/translations/thumbnails after N days or N entries; show cache size in settings with "Clear Cache" button.
   - *Why:* Memory-friendly; prevents unbounded disk growth.

10. **Virtual Scrolling for Long Lyrics** — Only render visible lyric lines in the DOM; critical for long songs or fullscreen mode.
    - *Why:* Memory-friendly; keeps DOM small.

### P2 — Medium Effort, High Differentiation

11. **Karaoke Scoring / Sing-along Mode** — Use Web Audio API to compare user's microphone pitch against the melody (requires microphone permission). Show accuracy score.
    - *Why:* Differentiates from all competitors; gamifies lyrics.

12. **AI Lyrics Analysis** — Local LLM (via transformers.js or Python `transformers`) to explain song meaning, highlight metaphors, generate "story summary" per song.
    - *Why:* AI features are trending; educational angle fits your vocab notebook.

13. **Lyrics Sync Editor** — Let users manually adjust timing of lyric lines (offset per line) and save corrected LRC back to cache. Share corrected lyrics.
    - *Why:* Lyricify has "Lyricify Lines Creator"; power users love fixing bad sync.

14. **Spotify Connect / Queue View** — Show current Spotify queue, upcoming tracks, pre-fetch lyrics for next 3–5 songs.
    - *Why:* Reduces perceived latency when songs change.

15. **Dark Mode Toggle / Dynamic Theme from Wallpaper** — Extract dominant color from Windows wallpaper and apply as accent/theme automatically.
    - *Why:* Windows 11 integration; feels native.

16. **Lyrics Sharing** — Generate a shareable image (canvas-to-image) of the current lyric line with album art, for Instagram/Twitter stories.
    - *Why:* Viral growth; users love sharing what they're listening to.

### P3 — Polish & Quality of Life

17. **Keyboard Navigation & Shortcuts Overlay** — Press `?` to show cheat sheet of all hotkeys; ARIA labels throughout.
    - *Why:* Accessibility + power-user friendliness.

18. **Auto-Updater** — GitHub releases + `pywin32` auto-update check on startup; download and replace `.exe`.
    - *Why:* Users don't want to manually rebuild.

19. **Settings Import/Export** — Export preferences (theme, language, opacity, hotkeys) to JSON; import on new machine.
    - *Why:* User data portability.

20. **Lyrics Quiz / Language Learning Mode** — Hide translation, show romaji only, user guesses meaning; vocab notebook integration. Track "words learned" per language.
    - *Why:* Leverages your existing vocab notebook; educational differentiation.

---

## 7. Recommended Modernization Roadmap

### Phase 1: Visual Modernization (2–4 weeks)
- Replace inline SVG icons with Lucide/Phosphor icon system
- Add skeleton loading states
- Add accent color picker + font size controls
- Respect `prefers-reduced-motion`
- Clean up glassmorphism (subtle borders, less blur)

### Phase 2: Memory & Performance (1–2 weeks)
- LRU cache eviction for lyrics/translations/thumbnails
- Pause render loop when hidden/minimized
- Virtual scrolling for lyrics list
- Connection pooling for SQLite
- Compress thumbnails before base64

### Phase 3: New Features (4–6 weeks)
- Desktop lyrics overlay (always-on-top)
- System tray app
- Multiple lyrics sources (Genius fallback)
- Custom font/size controls
- Lyrics sharing image generator

### Phase 4: Architecture (ongoing)
- TypeScript for frontend
- Vite/esbuild build step
- Consider Tauri (Rust) or Electron for cross-platform (or keep pywebview for Windows-only simplicity)

---

## 8. Quick Wins You Can Do This Weekend

1. **Icon swap** — Replace all inline SVGs with `<i data-lucide="..."></i>` from lucide CDN (~1 hour)
2. **Skeleton loader** — Add CSS skeleton classes + show during fetch (~2 hours)
3. **Cache clear button** — Add "Clear Lyrics Cache" in settings (~1 hour)
4. **Pause animation on hide** — Wrap `requestAnimationFrame` with `document.visibilityState` check (~30 min)
5. **Accent color variable** — Add `--accent` CSS variable + color picker in settings (~1 hour)

---

## 9. Bottom Line

Your app has **strong unique differentiators** (vocab notebook, word lookup+TTS, sleep timer, Discord RPC, ghost mode, boss key) that competitors lack. The core functionality works well. The main work needed is **visual modernization** (icons, CSS architecture, loading states) and **memory hygiene** (cache eviction, render loop pausing). If you address those plus add a **desktop overlay** and **tray icon**, you'd have a top-tier Spotify lyrics companion on Windows.
