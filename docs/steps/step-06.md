> Suggested reading (in docs/plan/): 03-architecture.md

### Step 6. Rate limits and abuse protection

Branch `feat/rate-limits`.

Because the API has a public URL and Cloud Run bills per use, protect it in the app. State can be in memory because there is only ever one instance.

- Run uvicorn with `--proxy-headers` and trust Cloud Run's `X-Forwarded-For` to find the client IP (the Dockerfile passes `--forwarded-allow-ips='*'`; document why that is acceptable behind Cloud Run).
- Limits per client IP (one method for everything: a **sliding-window limiter**, a `SlidingWindowLimiter` class that keeps a deque of recent timestamps per key and allows at most N events in the last W seconds, with idle keys cleaned up periodically; do not also implement token buckets; values configurable in `settings.py`; suggested defaults): create room 5 per minute; join attempts 20 per minute; **failed joins (unknown code) 10 per minute** (the code space is small, so this stops guessing); at most 20 concurrent WebSocket connections per IP; at most 20 inbound WebSocket messages per second per connection (close with 1008 when exceeded).
- Global caps: at most 200 rooms and 1,000 concurrent WebSocket connections in memory; beyond that, creating rooms returns 503 with a friendly message.
- Return `429` with a `Retry-After` header; the frontend shows a friendly message (handled in the lobby step).
- Tests: each limit triggers and recovers, the limits are per IP, and limits don't affect a normal 10-player game.

**Review checklist:** limits are configurable by env; a normal game never hits them; the proxy-header handling is explained in the PR.

---
