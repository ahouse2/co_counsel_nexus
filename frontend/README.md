# Co-Counsel Frontend

A Vite + React workspace delivering conversational research, evidence review, and historical timeline insights with resilient offline behaviour. Features a cinematic neon-themed UI with Tailwind CSS, shadcn/ui, and Radix primitives.

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

## Working with the Frontend

### Development Workflow

1. **Start the development server:**
   ```bash
   npm run dev
   ```
   This will start the Vite development server with hot module replacement.

2. **Connect to backend services:**
   - Ensure the backend is running on http://localhost:8000
   - The frontend will automatically proxy API requests to the backend

3. **Component Development:**
   - Components are organized in domain-specific modules under `src/components`
   - Each module contains related UI components and panels
   - Shared utilities are in `src/lib` and `src/hooks`

4. **Styling:**
   - Uses Tailwind CSS with custom design tokens
   - shadcn/ui components built on Radix primitives
   - Framer Motion for animations and transitions
   - Design tokens defined in `src/styles/design-tokens.css`

### Project Structure
```
src/
├── components/          # UI components organized by feature
│   ├── graph-explorer/  # 3D graph visualization components
│   ├── evidence/        # Evidence management UI
│   ├── trial-university/ # Educational content components
│   ├── mock-trial/      # Mock trial arena components
│   └── ui/             # Shared UI components (shadcn/ui)
├── hooks/              # Custom React hooks
├── lib/                # Utility functions and shared logic
├── styles/             # Global styles and design tokens
└── App.tsx             # Main application component
```

## Architectural Overview

### Layout
- **Chat workspace** — Streams answers from `/query` via WebSocket (`/query/stream`) with HTTP fallback.
- **Citation review** — Evidence cards with pop-out panels, search, and metadata derived from backend graph enrichment.
- **Timeline explorer** — Cursor-based fetches against `/timeline`, reusing cached events for offline resilience.
- **Graph Explorer** — 3D visualization of case relationships using React Three Fiber with neon-glass nodes, bloom, and depth-of-field effects.
- **Evidence Upload** — Drag-and-drop zone with glowing progress arcs and AI-generated summary tiles.
- **Trial University** — Holo-screen video lessons with interactive subtitles and progress tracking.
- **Mock Trial Arena** — Live video conferencing with draggable exhibits and real-time transcription.

### Design System
- **Tailwind CSS** — Custom theme with cinematic color palette, radii, shadows, and motion tokens.
- **shadcn/ui** — Accessible UI components built on Radix primitives with cinematic styling.
- **Framer Motion** — Smooth animations and transitions throughout the interface.
- **Design Tokens** — CSS variables for consistent styling across components.

### Data Flow
1. `QueryContext` orchestrates chat state, caching (IndexedDB), and telemetry hints.
2. `useWebSocket` handles streaming tokens with retry and HTTP fallback.
3. Service worker (`public/sw.js`) caches shell assets and API responses using stale-while-revalidate.

### Accessibility & UX Guarantees
- Landmark navigation, skip link, and keyboard shortcuts (`Ctrl + Enter`, `g`, `n`, `p`).
- `aria-live` regions announce streaming updates; pop-out panels trap focus and close with `Esc`.
- High-contrast theme toggle stored persistently; respects `prefers-reduced-motion`.
- Focus states and keyboard navigation for all interactive components.

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