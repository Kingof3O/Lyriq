# Lyriq component specification

The rule for implementation is **typography first, chrome second**. Do not convert this design into a dashboard of rounded cards. Cards are permitted only for genuinely detached surfaces such as the command palette, a destructive confirmation, or a small inspector.

## 1. Window shell

- Base artboard: 1440×900 for reference. Must scale down to 960×640 without losing controls.
- Top bar: 58 px.
- Border: only a 1 px bottom hairline at ~4–6% white in dark mode.
- App mark: 24×24, followed by `Lyriq`, then the current surface name in muted text.
- Track identity is centered in the top bar, not in a sidebar.
- Native/minimize/maximize/close hit regions remain at least 40×32 even when icon glyphs look smaller.
- Draggable regions must exclude buttons, search fields, sliders, links, and the center track identity.

## 2. Lyric line stack

### Active line
- 46 px default; user range 32–64 px.
- Weight 690 or nearest supported variable weight.
- 1.08 line height.
- Left playhead rail: 3 px, rounded, 5 px inset from top/bottom.
- Rail uses brand violet. Do not fill the entire line background.
- Allow wrapping to a maximum of two visual lines before automatic scale-down.

### Near lines
- 29 px default.
- Opacity target 0.62.
- Far lines opacity 0.25–0.35.
- Never blur text in the production UI; the reference blur only indicates perceptual recession. Use opacity and slight scale only.

### Translation
- 22 px default, brand-soft violet.
- Display 12–16 px below active lyric.
- Translation is subordinate to original unless user selects Translation-only mode.

### Romanization
- 14 px, muted.
- Display 6–8 px below translation.
- Suppress automatically when it would create more than 3 visible text tiers and viewport height is constrained.

## 3. Playback dock

- 720×64 at desktop reference size.
- Centered 22 px above window bottom.
- Radius 18 px; border only 1 px. Surface opacity ~94% in dark mode.
- Dock has three zones: status / transport / view controls.
- Progress is a 2 px line fused to the dock bottom edge. It is not a conventional thick media slider until hovered.
- Hovering progress expands hit target to 16 px while keeping visual line 2 px.
- Scrubbing must show timestamp above cursor after 250 ms hover.

## 4. Pill tags

Use only for compact state such as `DUAL`, language pair, `LIVE +12ms`, or provider capability. Tags are not primary navigation.
- Height 24–26 px.
- 1 px hairline border.
- No saturated fills except selected segmented controls.

## 5. Study Lens inspector

- Right inspector: 358 px desktop width.
- Opens only after word selection or explicit Study action.
- Main lyric canvas compresses; it does not get covered.
- The selected word receives a 2 px underline plus very subtle 8% violet wash.
- Order: word → pronunciation → grammatical chips → concise definition → context note → source lyric → notebook actions.
- Save action is persistent at inspector bottom.
- Closing returns focus to the selected lyric word.

## 6. Lyrics Search

- This is a focused workflow, not a dialog over Reader.
- Candidate rows are 88–96 px and separated by hairlines.
- Selected candidate gets a 3 px brand rail and a faint left-to-right violet wash.
- Required fields: provider, confidence score, synced status, duration/delta, language, translation availability, miniature timing density, source id when available.
- Inspector width 360 px.
- Never hide why a match scored highly/poorly.

## 7. Command palette

- Width 610 px at desktop reference.
- Opaque carbon surface; no heavy glassmorphism.
- Max visible results: 8–10 before internal scrolling.
- Selected result uses a 2 px violet rail and low-contrast surface change.
- Keyboard flow: typing → Up/Down → Enter; Esc closes; Ctrl+K toggles.
- Footer always shows the relevant keyboard affordances.

## 8. Mini Island

- Default: 680×118 px reference; minimum practical width 480 px.
- Radius 28 px.
- Zones: track identity 190 px / lyric flex / transport 140 px.
- Controls fade to 35% after 2 s idle; lyric remains at 100%.
- Hover restores controls within 120 ms.
- Bottom 2 px progress rail.
- Empty surface is draggable; interactive controls are not drag regions.

## 9. Ghost Overlay

- No visible window chrome or panel.
- Active lyric centered; translation below.
- Use text shadow / contrast sampling for readability, not a background box.
- Click-through mode must have a clear global escape path via Ctrl+Shift+G.
- When click-through is off, expose a 44×4 px drag affordance at top center on hover only.
- Keep a tiny state hint top-right; fade after 1.5 s.

## 10. Settings

- Text-only category rail, 220 px.
- Main area uses groups separated by hairlines rather than cards.
- Every appearance setting that affects lyrics should update the preview immediately.
- Never mix application settings with current-song controls.

## 11. Controls

- Minimum pointer hit target: 32×32; critical controls 40×40.
- Keyboard focus ring: 2 px brand outline + 2 px offset on dark surfaces.
- Disabled state: 40% opacity, no pointer interaction.
- Switch: 40×22 px, 16 px thumb.
- Segmented control: 36 px height including 3 px internal padding.
- Slider track: 4 px visual, 18 px hit target.

## 12. Icons

Use one SVG stroke family at 1.7–2.0 px optical weight. Do not mix emoji or platform glyphs with the custom icon family. The Lyriq brand symbol is not a generic navigation icon; reserve it for brand/app identity and the small lyric playhead motif.
