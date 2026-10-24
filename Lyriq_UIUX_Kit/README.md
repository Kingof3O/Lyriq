# Lyriq UI/UX Agent Handoff Kit

This package turns the Lyriq brand into an implementation-ready desktop UI system.

## Start here
Open `01_Screens/01-reader-dark.png`, then read `04_Agent_Handoff/IMPLEMENTATION_SPEC.md`.

## Folder map
- `00_Overview/` — AI concept-board reference; useful for mood only. The canonical layout is the rendered screens.
- `01_Screens/` — canonical visual references.
- `02_Design_System/` — exact design tokens and component rules.
- `03_Flows/` — user flows and UI state model.
- `04_Agent_Handoff/` — implementation requirements, interactions, acceptance tests, copy/paste agent prompt.
- `05_HTML_References/` — static HTML/CSS references that reveal spacing/layout logic. They are not intended as production code.
- `06_Brand_Reference/` — core Lyriq logo/icon assets used by the mockups.

## Visual hierarchy
1. Active lyrics
2. Translation / romanization
3. Current track identity
4. Playback state
5. Secondary controls
6. Navigation/settings only when invoked

## Important
The `AI-concept-board-reference.png` is **not** the target screen architecture. It is retained only as a mood/reference artifact. The purpose-built PNGs in `01_Screens/` supersede its generic dashboard layout.
