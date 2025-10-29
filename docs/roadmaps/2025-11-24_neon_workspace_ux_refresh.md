# 2025-11-24 — Neon Workspace UX Refresh

## Summary
- Established global neon design tokens for dark-mode cinematic presentation and applied them across chat, timeline, document, and simulation surfaces.
- Introduced an integrated documents workspace with inline viewer, citation search, and cross-linking from chat and timeline pop-outs.
- Enabled streaming markdown rendering for assistant responses with interactive citation chips and external source shortcuts.
- Expanded voice console with live transcription overlays, automated session refresh, and persona-aware controls.
- Reoriented navigation into a responsive sidebar for Chat, Timeline, Documents, Trial University, and Mock Court experiences with keyboard shortcuts.

## Acceptance Criteria
1. **Design Tokens**
   - [x] `frontend/src/styles/index.css` defines CSS variables for background, surfaces, accent colors, typography, radii, and shadows aligned with neon cinematic spec.
   - [x] Layout components consume tokens (no raw hex duplicates for core palette).

2. **Documents Workspace**
   - [x] Documents section shows inline viewer populated when a citation is selected from chat, timeline, or the list itself.
   - [x] Timeline pop-out modal exposes citation buttons that activate the viewer.
   - [x] Document viewer lists related timeline events with anchors back to the timeline.

3. **Chat Experience**
   - [x] Assistant responses render markdown progressively (lists, code, emphasis) using `react-markdown` with GFM support.
   - [x] Citation chips expose “Open source” links and selecting a chip opens the document viewer.

4. **Voice Console**
   - [x] Recording/Playback controls remain functional and display waveform feedback.
   - [x] Live transcription overlay updates within 5 seconds of session refresh and reports confidence metrics.

5. **Responsive Navigation**
   - [x] Sidebar collapses into a horizontal scroller below 960px while preserving tab semantics.
   - [x] Keyboard shortcuts: `g` focuses Timeline, `d` focuses Documents, `n/p` iterate events, `Ctrl/Cmd+Enter` sends chat message.

6. **Accessibility & QA**
   - [x] Primary interactive controls provide focus styles meeting 3:1 contrast.
   - [x] `npm run lint` and `npm run test` pass without warnings.

## Visual Reference
![Neon workspace overview](images/neon-workspace-overview.png)

## Follow-ups
- Evaluate motion presets for knowledge hub cards respecting `prefers-reduced-motion`.
- Extend timeline modal with event-specific AI reasoning traces.
