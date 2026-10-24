# Interaction and micro-motion specification

## Pointer
- Single click lyric: focus line; if synced, seek only when user clicks explicit timestamp/seek affordance. Do not make every lyric line a hidden seek target by default.
- Double click word: open Study Lens and select token.
- Right click lyric: context menu (copy original, copy translation, save line, edit local LRC, search alternate lyrics).
- Wheel/trackpad: manual lyric scroll temporarily suspends auto-follow for 4 seconds. Show a small `Return to live` affordance while detached.
- Clicking `Return to live` immediately recenters active line.

## Keyboard
- Ctrl+K: command palette.
- F11: immersive.
- Esc priority: modal → palette → search preview → focused workspace → immersive.
- Ctrl+Shift+G: Ghost toggle, system-wide.
- Ctrl+Shift+M: Mini toggle, system-wide.
- Ctrl+Shift+H: Boss hide/show, system-wide.
- Ctrl+Shift+L: cycle lyric view.
- Ctrl+Shift+Space: play/pause.

## Hover
- Reader top controls: opacity 55% idle → 100% hover.
- Playback progress: 2 px visual → 4 px visual on hover, 16 px hit region.
- Mini Island controls: 35% after 2 s idle → 100% in 120 ms hover.
- Ghost state hint: visible for 1.5 s after mode change; then 20% until hover.

## Focus
- Command palette traps focus until closed.
- Study Lens does not trap focus; Tab can move back to Reader controls.
- Lyrics Search is a full workspace and owns document focus.

## Auto-follow
Auto-follow pauses when user scrolls farther than one active-line height from the live position. It resumes after 4 s of no manual scroll **only if** the user has not moved more than 4 lines away; otherwise require `Return to live`.

## Seek
On seek, freeze lyric movement until the new playback anchor arrives or 300 ms elapses. Then snap/tween once to the new active index. Do not animate through every skipped line.
