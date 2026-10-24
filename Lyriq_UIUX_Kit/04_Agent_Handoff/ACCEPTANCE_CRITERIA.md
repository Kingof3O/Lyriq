# Acceptance criteria

A build is not visually complete until all items below pass.

## Reader
- [ ] No permanent left/right navigation sidebar.
- [ ] Active lyric is the strongest visual element on screen.
- [ ] Violet playhead rail is 3 px and visually aligned to active text block.
- [ ] Inactive lyrics recede via opacity/scale, not Gaussian blur.
- [ ] Translation and romanization never overpower original text.
- [ ] Dock progress is 2 px at rest and has a larger invisible hit target.
- [ ] Reader remains usable at 960×640.

## Mode behavior
- [ ] Mini uses a dedicated layout; it is not scaled-down Reader.
- [ ] Ghost has zero visible window panel/chrome.
- [ ] Global Ghost toggle always restores interaction.
- [ ] Command palette works entirely by keyboard.
- [ ] Study Lens preserves playback/scroll state when opened/closed.
- [ ] Lyrics Search preview does not restart playback.

## Settings
- [ ] Appearance changes preview live.
- [ ] Categories use a slim text rail, not a card dashboard.
- [ ] Theme change preserves layout exactly.

## Motion/performance
- [ ] No backend-to-WebView 60/144Hz position spam.
- [ ] One client interpolation loop maximum.
- [ ] No full lyric-list rerender each frame.
- [ ] Reduce Motion works.
- [ ] Paused state does not run an unnecessary continuous animation loop.

## Visual integrity
- [ ] No emoji used as application icons.
- [ ] No Spotify green as Lyriq identity.
- [ ] No excessive glassmorphism/backdrop blur.
- [ ] Cards are reserved for detached surfaces only.
- [ ] Dynamic album accent never replaces brand violet for focus/selection.
