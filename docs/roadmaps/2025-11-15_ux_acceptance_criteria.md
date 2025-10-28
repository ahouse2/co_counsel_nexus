# 2025-11-15 UX Acceptance Criteria — Chat, Citations, Timeline

## Global Experience
- **Accessibility**
  - WCAG 2.2 AA compliance for keyboard navigation, focus visibility, and ARIA semantics.
  - High-contrast theme toggles persist between sessions and respect prefers-reduced-motion.
  - Screen-reader announcements for live updates (chat streaming, timeline refresh).
- **Offline Resilience**
  - First load caches shell assets; chat history and timeline entries available after reconnect.
  - Cache invalidation executes on version bump without user intervention.

## Chat Workspace
- **Live Response Streaming**
  - WebSocket `/query/stream` delivers tokens with <200ms UI latency; fallback completes via REST within 3s of message send.
  - Partial responses append without reflow; aria-live "polite" region announces increments.
- **Message Management**
  - Users can resend last prompt, edit drafts, and see network status indicator.
  - Error states display remediation guidance, offering retry or offline queueing.

## Citation Evidence Panels
- **Pop-out Panels**
  - Evidence cards open in detachable modal with focus trap, ESC close, and accessible title.
  - Panels support text scaling to 200% without loss of content or functionality.
- **Traceability**
  - Each citation links back to originating chat turn and relevant timeline events.
  - Metadata includes document title, confidence score, and entity tags.

## Timeline Explorer
- **Data Fidelity**
  - Events enriched with entity highlights and relation tags from graph metadata.
  - Filtering by entity, date range, and confidence thresholds yields deterministic results.
- **Interactivity**
  - Keyboard shortcuts (`g` to toggle timeline, `n`/`p` to navigate events) function across browsers.
  - Live counter of rendered events updates when streaming chat references spawn new timeline entries.

## Telemetry & Observability
- **Metrics Exposure**
  - Backend counters for timeline reads, filter applications, and metadata enrichment success accessible via `/metrics` scrape.
  - Frontend logs instrumentation events (Page load, send prompt, open evidence) through existing telemetry client without regressions.

## Acceptance Validation
- Automated test suite covers timeline metadata persistence, telemetry counter increments, and offline cache registration.
- Manual QA checklist executed for keyboard navigation, screen reader flow, offline reconnection, and streaming fallback.
