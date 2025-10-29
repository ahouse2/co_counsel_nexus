# Build Log — 2025-11-24 Neon Workspace Refresh

## Summary
- Added neon tokenized dark theme to global stylesheet with responsive sidebar layout.
- Wired streaming markdown chat bubbles, interactive citation chips, and integrated document viewer panel.
- Enabled timeline pop-outs with citation navigation and enhanced voice console transcription overlay.

## Commands
- `npm run lint`
- `npm run test`

## Notes
- Document viewer dispatches `focus-timeline-event` custom events so timeline state can synchronise focus across panels.
- Live transcription polls session detail every 5 seconds; future iteration could switch to server-sent events when available.
