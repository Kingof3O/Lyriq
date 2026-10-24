# Production Refactor Plan — SpotifyLyrics v2.5 → v3

**Spec:** User-briefed four-phase production refactor (2026-10-24). This plan is the execution map.
**Branch:** `refactor/v3` (baseline commit `628e74a`)
**Global constraints**

- Windows-only desktop app: Python 3.12, pywebview 6.2, winsdk SMTC, SQLite, vanilla JS/CSS.
- Do not break: vocabulary notebook, history, favorites, sleep timer, global hotkeys, ghost mode, boss key, LRC/SRT/HTML exports, mini mode, fullscreen mode, Discord RPC toggle.
- No `TODO` placeholders, no truncated functions, no silent `except: pass` added in new code.
- All mutable data goes under `%LOCALAPPDATA%\SpotifyLyrics\` unless `portable.flag` exists beside the exe, then `./data/`.
- Keep the app usable offline; no new network requirement for core UI.
- Verify with `python -m compileall`, `python -m unittest discover -s tests`, and a headless UI smoke test where possible.
- Commit each task with a descriptive message.

## Task 1 — Persistence foundation, cache singleton, settings, offsets

Create `app_paths.py`; rewrite `cache_service.py`; update `lyrics_service.py` and `translator_service.py` to use one shared thread-safe cache. Add schema migrations, settings table, `song_offsets`, thumbnail cache with size cap, translation cache pruning, `clear_cache()`. Add `tests/test_cache_service.py` with `unittest` using a temp data dir. Verify persistence across two CacheService instances and that no path resolves to `_MEIPASS` under a simulated frozen layout.

## Task 2 — Lyric pipeline correctness, IPC deltas, unsynced, translation alignment, pinyin

Add generation IDs/cancellation in `main.py` and service loops. Change `media_listener.py` to send full track data only on track change and lightweight deltas otherwise. Update `main.py`/JS bridge for `updatePlaybackState`. Split `is_synced` handling and ensure plain lyrics do not highlight/scroll. Harden translation delimiter validation with per-line fallback. Add optional `pypinyin` support and dynamic romanization label. Add `escape_html`/safe export handling in JS? (frontend task owns XSS, backend exposes no HTML). Add unit tests for parser/translation alignment.

## Task 3 — Frontend state, IPC, persistence, unsynced, offset, safe rendering

Rewrite `web/app.js` around a single `AppState`. Implement `pywebviewready` init, `get_settings`/`save_settings`, per-song offset, `updateTrack`/`updatePlaybackState`/interpolation with `performance.now()`, unsynced static mode, skeletons, safe DOM rendering for history/vocab, safe poster export, custom toast confirm, and the Ctrl+K command palette. Preserve all existing features. Add JS syntax check via `node --check`.

## Task 4 — 2026 visual redesign, icons, themes, performance, custom controls

Rewrite `web/index.html` and `web/style.css`; replace all emoji with an inline SVG icon dictionary; add `[data-tooltip]` + aria labels; remove Google Fonts; system font stack. Replace orbs/backdrop blur/per-line blur/fake spectrum/radar with static album backdrop, dynamic accent, light/dark/system/OLED themes, custom switches/selects/ranges, segmented controls, lyrics-first layout, skeletons, low-power mode, reduced motion. Gate RAF loops. Preserve all controls and JS IDs where practical; coordinate with Task 3's AppState.

## Task 5 — Multi-provider lyrics engine + metadata normalizer + local LRC + NetEase

Add `lyrics_providers.py` with a provider interface, metadata normalizer, scoring, local `.lrc` provider, LRCLIB provider, NetEase fallback; wire into `lyrics_service.py`; expose manual search/select and local LRC directory through `main.py`; show provider badge in UI. Add tests for normalization and scoring. Keep LRCLIB as a primary fallback and never crash on provider errors.

## Task 6 — Single instance, system tray, window state, build optimization

Add named-mutex single-instance guard and focus-existing behavior. Add a ctypes Win32 tray icon with Show/Hide, Play/Pause, Mini, Settings, Quit; add close-to-tray and start-with-Windows toggle. Persist/restore window x/y/width/height/always-on-top/fullscreen/mini. Update `build.py` and `SpotifyLyrics.spec` to stop `collect_all('winsdk')` and bundle only required winsdk modules + `icon.ico`; verify a build if feasible.

## Task 7 — Integration verification and handoff

Run compileall, unittest, node --check, a headless UI smoke test with injected track/lyrics, and a PyInstaller build check. Fix integration defects. Update README version/run instructions and add a verification checklist. Commit.
