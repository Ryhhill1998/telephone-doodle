> Suggested reading (in docs/plan/): 01-product-spec.md (robustness requirements); 03-architecture.md; 04-ui-design-brief.md

### Step 8. Frontend foundation and lobby

Branch `feat/lobby`. Requires Step 7 approved.

- Routing (`react-router`): `/` (create or join) and `/room/:code`. The room page shows the right screen for the current phase. Firebase Hosting rewrites every path to `index.html`, so deep links work.
- Config: `src/config.ts` reads `import.meta.env.VITE_API_URL` (empty in dev, so requests go through Vite's proxy) and derives the HTTP and `ws(s)://` base URLs from it.
- `game/useGameSocket(code)` hook: connects with the token from `localStorage`, auto-reconnects (immediately on close code 1012, then exponential backoff), exposes the latest `state`, a `connection` status and `send()`. Typed message and state types in `frontend/src/game/types.ts` mirroring the backend schemas (one file, with a comment where it mirrors Pydantic).
- Home page and Lobby matching the design: create room or join with code and name; lobby shows the code (big, with copy button), the player list with connected status, numbered seat order with a host-only Shuffle order button and remove (cross) buttons, host-only Start button (disabled under 3 players). Friendly handling of `429` and `503`.
- Design tokens from section 4 as CSS custom properties in one stylesheet. Mobile-first, 44px minimum tap targets, visible focus.
- The "Reconnecting..." banner and the "Waking things up..." message for slow first connections.
- **Rejoin:** keep `{code, token}` in `localStorage`; the home page shows "Rejoin room KQFM" while a saved seat exists (and clears it if the server says the room is gone or the player was removed). The socket hook also reconnects immediately on `visibilitychange` (tab visible again) and the `online` event, which covers locked phones.
- **Frontend tests (vitest + Testing Library):** the socket hook against a fake `WebSocket` (connect, reconnect after 1012, backoff, reconnect on visibility change, state updates), the Home and Lobby screens (create, join, error and `429` messages, host-only controls visible only to the host, shuffle and remove send the right messages, Start disabled under 3 players), and the rejoin flow.

**Review checklist:** two browser tabs can create, join and see each other live; refreshing a tab rejoins the same seat; restarting the dev backend shows the banner and recovers.

---
