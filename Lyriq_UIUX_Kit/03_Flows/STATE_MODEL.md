# UI state model

## Window modes
`reader | immersive | mini | ghost | settings | lyrics_search`

`settings` and `lyrics_search` are focused workspaces. They are not overlays on Reader.

## Reader overlays
`none | command_palette | study_lens | modal`

Only one of `command_palette`, `study_lens`, or `modal` may own keyboard focus at a time.

## Playback state
`waiting | loading_track | resolving_lyrics | playing | paused | unavailable | error`

## Lyric display state
- source: `local | lrclib | netease | manual`
- timing: `synced | unsynced`
- view: `dual | translation | original`
- romanization: boolean
- translation: `idle | loading | ready | partial | error`

## Priority rules
1. Global hotkey safety (exit ghost/click-through) wins over all overlays.
2. Modal confirmation wins keyboard focus.
3. Command palette wins over Reader shortcuts except media global hotkeys.
4. Study Lens owns word-navigation keys only while focused.
5. Reader receives line navigation/scroll otherwise.
