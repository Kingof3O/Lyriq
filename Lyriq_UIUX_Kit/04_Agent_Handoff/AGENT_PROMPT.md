# Copy/paste prompt for the coding agent

You are implementing the Lyriq Windows desktop UI from an approved design handoff.

Read these files before touching UI code, in this order:
1. `04_Agent_Handoff/IMPLEMENTATION_SPEC.md`
2. `02_Design_System/COMPONENT_SPEC.md`
3. `04_Agent_Handoff/INTERACTION_SPEC.md`
4. `04_Agent_Handoff/SCREEN_BLUEPRINTS.md`
5. `04_Agent_Handoff/ACCEPTANCE_CRITERIA.md`
6. `02_Design_System/tokens.json`
7. inspect every PNG in `01_Screens/`
8. use HTML references in `05_HTML_References/` for spatial guidance, not as production code.

Design constraints are binding:
- Reader MUST NOT have a persistent navigation sidebar.
- Do not reinterpret the product as a generic music dashboard.
- Lyrics dominate the default screen.
- Use hairlines and whitespace before creating rounded cards.
- Brand violet is persistent identity; album color is contextual only.
- Mini and Ghost are independent compositions.
- Use SVG icons, never emoji glyphs.
- Keep the backend/frontend boundary event-driven; do not send playback position at display refresh rate.

Implementation strategy:
- First map existing UI components and state management.
- Preserve working backend/SMTC/provider/persistence behavior.
- Introduce design tokens centrally.
- Implement Reader shell + lyric stack + dock before secondary screens.
- Then implement Study Lens, Lyrics Search, Command Palette, Settings, Mini, Ghost.
- Add responsive/compact rules.
- Add reduced motion and keyboard focus behavior.
- Compare implementation against reference PNGs at 1440×900.
- Run through every acceptance criterion and fix failures before considering the UI complete.

When existing behavior conflicts with the design, prefer preserving functional behavior while adapting presentation. Do not delete working features merely because they are not visible in the default Reader; route them through Command Palette, context menus, Settings, or focused workspaces.
