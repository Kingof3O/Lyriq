# Lyriq UI/UX implementation specification

## Product objective

Lyriq is a **lyrics instrument**, not a general music player. Spotify remains responsible for library/browsing. Lyriq owns reading, synchronization, translation, romanization, study, lyric-source control, and desktop overlay behavior.

The UI must feel quiet when nothing needs attention and become information-dense only when the user asks for diagnostics/search/study/settings.

## Non-negotiable design principles

1. **Lyrics are the primary surface.** Do not create a permanent app sidebar in Reader.
2. **Contextual complexity.** Study/search/settings appear only when invoked.
3. **One permanent brand accent.** Violet is identity. Album-derived color is a temporary `--live-accent`; never replace brand violet globally.
4. **Hairlines over cards.** Prefer separators and whitespace. Avoid a grid of rounded rectangles.
5. **No Spotify imitation.** No Spotify green, no Spotify navigation patterns, no recreation of its Now Playing screen.
6. **Motion follows playback semantics.** Transitions should imply time/continuity, never decorative bouncing.
7. **Small-window quality matters.** Mini/Ghost are first-class surfaces, not shrunk Reader.

## Recommended frontend structure

```text
ui/
  shell/
    WindowChrome
    TopBar
    FocusManager
  reader/
    ReaderStage
    LyricStack
    LyricLine
    TranslationTier
    RomanizationTier
    PlaybackDock
    ReaderStatus
  study/
    StudyLens
    WordHeader
    WordContext
    NotebookAction
  search/
    LyricsSearchPage
    CandidateList
    CandidateRow
    MatchInspector
  palette/
    CommandPalette
    CommandGroup
    CommandRow
  mini/
    MiniIsland
  ghost/
    GhostOverlay
  settings/
    SettingsPage
    SettingsRail
    AppearancePreview
  primitives/
    IconButton
    Pill
    SegmentedControl
    Switch
    Slider
    Select
    Hairline
```

## Reader layout

### Desktop >= 1100 px wide
- Top bar 58 px.
- Reader content max width ~920 px.
- Stage centered horizontally.
- Active lyric baseline should visually sit around 52–58% viewport height, not dead center, because upcoming lines need more perceived space below.
- Bottom dock: 720×64, 22 px bottom offset.

### Compact 960–1099 px
- Stage max width = viewport - 120 px.
- Dock = min(720 px, viewport - 48 px).
- Hide nonessential top status chips before reducing lyric size.

### Below 960 px
This desktop app may still be resizable smaller. Preserve usability:
- Active lyric min 32 px.
- Translation min 17 px.
- Collapse dock right-zone controls into `•••` when width < 620 px.
- Do not introduce a sidebar.

## Lyric virtualization

Only mount a window around the active index, e.g. active ± 12 lines. The visual stage normally shows 5–7 lines but keeping extra mounted lines prevents pop-in during fast scroll/seek.

Each normalized lyric line should expose:

```ts
interface UILyricLine {
  id: string;
  startMs: number | null;
  endMs: number | null;
  original: string;
  translation?: string;
  romanization?: string;
  words?: Array<{ text:string; startMs?:number; endMs?:number; lemma?:string }>;
}
```

Do not derive UI identity from array index because candidate changes and translation refreshes can reorder or replace data.

## Playback interpolation contract

Frontend receives playback anchor events, not 60/144 fps position messages:

```ts
interface PlaybackAnchor {
  positionMs: number;
  monotonicSentAtMs: number;
  state: 'playing' | 'paused';
  rate: number;
  trackInstanceId: string;
}
```

While playing:
`estimatedPosition = anchor.positionMs + (performance.now() - anchor.receivedAt) * anchor.rate`

Resync on:
- seek
- pause/play
- track change
- drift >= 120 ms
- periodic heartbeat around 2–4 s

Animation frame may run at display refresh, but it reads local interpolated time only.

## Lyric transition behavior

When active line changes:
- old active → near state: 180 ms, ease `cubic-bezier(.2,.8,.2,1)`
- new active → active state: 220 ms
- stage Y offset interpolation: 220–260 ms
- translation/romanization opacity: 120–180 ms after active line locks
- reduce-motion: no scale/position tween; use 100–120 ms opacity crossfade

Never animate every word unless word timing exists. For line-timed LRC, use line-level progression only.

## Karaoke progress

If word timing exists, render a foreground text mask using per-word timing. If only line timing exists, either:
1. keep entire active line solid, or
2. use a subtle left-to-right progress wash only when duration is trustworthy.

Do not fake syllable timing.

## Live accent extraction

Backend or frontend may extract album color. Normalize to ensure contrast and avoid ugly mud:
- saturation clamp 35–78%
- lightness clamp 48–72% for dark mode
- never map live accent onto primary body text
- live accent may affect progress, ambient glow, or tiny metadata only
- brand violet remains study/focus/selection color

## Surface-specific behavior

### Study Lens
- Open on double-click or explicit context action.
- Delay network dictionary request until local tokenization/romanization result is shown.
- Cancel stale request if selection changes.
- Panel remains open when playback advances, but source-line context should remain the line where the word was selected.

### Lyrics Search
- Freeze candidate list for current `trackInstanceId`.
- Do not reshuffle rows while user is comparing them; append late providers or show `new result` marker.
- Preview swaps lyric timeline in memory only; committing persists selected source/override.
- `Esc` during preview returns to previous candidate before closing page.

### Mini Island
- Save independent mini window bounds.
- Text truncation: track title can ellipsize; active lyric gets priority and may use two lines if island height is expanded.
- Idle fade affects controls, not text.

### Ghost
- Rendering layer should be transparent and non-activating when click-through is enabled.
- Global shortcut must always restore pointer interaction even if WebView focus is elsewhere.
- Persist per-monitor position.

## Error states

### Waiting for Spotify
Use center-stage copy only:
`Waiting for Spotify` + short helper text. No modal.

### Lyrics resolving
Keep track metadata visible. Show three skeleton lyric bars in the stage using very low-contrast shimmer. Avoid spinners in the center.

### No synced lyrics
Render unsynced lyrics in reading mode and show a small `UNSYNCED` state tag. Playback dock remains normal.

### Provider failure
Do not surface individual provider errors unless all providers fail or the user is in Lyrics Search/Diagnostics.

### Translation failure
Original lyrics continue normally. Translation tier shows `Translation unavailable` only for active line and retry is placed in context menu/inspector, not as a persistent banner.

## Accessibility

- All controls must be keyboard reachable except click-through Ghost state by definition; global escape hotkey remains available.
- Focus ring visible at 3:1 contrast against adjacent surface.
- Do not communicate synced/unsynced or selected state by color alone.
- Respect Windows text scaling up to at least 125%; avoid clipping top-bar controls.
- User can disable motion.
- Use semantic button/slider/select roles in WebView.
- Announce track changes and provider errors politely; do not announce every lyric line by default because that would overwhelm screen readers.

## Performance budget

Target the frontend itself, excluding WebView runtime:
- Reader idle after load: no continuous layout thrash.
- One requestAnimationFrame loop maximum, suspended when paused and no transition is active.
- Active lyric change should not trigger full list rerender.
- Avoid CSS backdrop-filter on large surfaces; Ghost uses text shadow rather than blur.
- Album ambient effect must be a single pseudo-element/bitmap, not multiple animated blurred layers.

## Persistence

Persist:
- reader bounds
- mini bounds
- ghost bounds by monitor identity
- last non-ghost mode
- pin/always-on-top
- selected theme/view/romanization/target language
- lyric scale
- reduced motion

Do not persist transient inspector/palette state.
