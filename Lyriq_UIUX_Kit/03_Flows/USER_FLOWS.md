# User flows

## A. Normal playback
1. App launches hidden or visible according to previous state.
2. SMTC reports current track.
3. Reader displays track identity immediately, even before lyrics arrive.
4. Lyrics resolver checks local override/cache, then remote providers.
5. First usable lyric payload renders.
6. Translation/romanization arrive progressively without reflowing the entire window.
7. Active line advances using local high-resolution interpolation between playback anchors.

## B. Wrong lyrics
Reader → `•••` or Ctrl+K → `Find another lyrics version` → Lyrics Search → choose candidate → Preview → `Use this version` → return to Reader at current playback position.

Important: candidate selection must never reset Spotify playback or jump the lyric timeline to 0.

## C. Study a word
Reader → double-click/tap word → Study Lens opens → dictionary/romanization loads → Save word → lightweight confirmation → close inspector → Reader returns to exact scroll/line state.

## D. Mini Island
Reader → Ctrl+Shift+M → transform window bounds to saved Mini Island rectangle → remain always-on-top if configured → Ctrl+Shift+M restores previous Reader bounds, not a default rectangle.

## E. Ghost Mode
Reader or Mini → Ctrl+Shift+G → save current interactive window style → show transparent lyric overlay → enable click-through → Ctrl+Shift+G always disables click-through first and restores interactivity.

## F. Command palette
Any interactive Lyriq window → Ctrl+K → search commands/history/settings → Enter runs command → palette closes unless command opens a second focused surface.

## G. Translation change
Reader view chip → select language → keep original lyric and timing stable → show loading placeholder only in translation tier → swap translated lines atomically when batch arrives → cache by lyric identity + target language + translation provider version.
