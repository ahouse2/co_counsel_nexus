# Co-Counsel Frontend

A Vite + React workspace delivering conversational research, evidence review, and historical timeline insights with resilient offline behaviour.

## Getting Started

### Prerequisites
- Node.js 20+
- npm 10+ (pnpm/yarn supported with equivalent commands)

### Installation
```bash
cd frontend
npm install
```

### Development Server
```bash
npm run dev
```
- Serves at http://localhost:5173 by default.
- Proxy base URL via `VITE_API_BASE_URL` when targeting a remote backend.

### Quality Gates
```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

## Architectural Overview

### Layout
- **Chat workspace** — Streams answers from `/query` via WebSocket (`/query/stream`) with HTTP fallback.
- **Citation review** — Evidence cards with pop-out panels, search, and metadata derived from backend graph enrichment.
- **Timeline explorer** — Cursor-based fetches against `/timeline`, reusing cached events for offline resilience.

### Data Flow
1. `QueryContext` orchestrates chat state, caching (IndexedDB), and telemetry hints.
2. `useWebSocket` handles streaming tokens with retry and HTTP fallback.
3. Service worker (`public/sw.js`) caches shell assets and API responses using stale-while-revalidate.

### Accessibility & UX Guarantees
- Landmark navigation, skip link, and keyboard shortcuts (`Ctrl + Enter`, `g`, `n`, `p`).
- `aria-live` regions announce streaming updates; pop-out panels trap focus and close with `Esc`.
- High-contrast theme toggle stored persistently; respects `prefers-reduced-motion`.

### Offline Behaviour
- Static shell cached during install.
- `/query` and `/timeline` responses cached for replay; chat/timeline state stored in IndexedDB.
- Offline indicator surfaces connectivity; submissions queue and replay when connection returns.

### Testing Strategy
- Vitest + Testing Library cover critical interaction flows.
- ESLint (with JSX a11y) and TypeScript enforce style and safety.

## Deployment
- `npm run build` emits artifacts in `dist/`.
- Configure hosting to serve `/sw.js`, `/manifest.webmanifest`, and fallback to `index.html`.

## Troubleshooting
- **WebSocket blocked** — Ensure backend exposes `/query/stream` over WS/WSS; fallback to HTTP will still produce answers.
- **Service worker cache stale** — Bump `CORE_VERSION` in `public/sw.js` to invalidate caches.
- **Accessibility regression** — Run `npm run lint` to surface JSX a11y violations.
