## 7. v1 backlog (do not build now, just list in README)

- Round timers (host toggle: off / 60 s / 90 s) with auto-submit
- Fuzzy-match scoring for guesses (the starting word is already stored, so round 1 can be scored against it; drawer and guesser both score), scoreboard
- Votes with limited votes per player, highlights reel, "drift" detection, awards (finished games are already saved for this)
- A way to look back at past games (a link or a history page)
- Stroke replay animation in the reveal
- Themed and custom family word packs
- Export a book as a shareable image or GIF
- Async play mode
- Hall of fame across game nights
- Remove a player **mid-game** (they would be auto-skipped for the remaining rounds, shown as skipped in the reveal; in v0 the host's Skip button covers this one round at a time), plus lock-room and ban for kicked players
- Drag to reorder seats in the lobby (v0 only has Shuffle order)
- **Observability dashboard** (Cloud Monitoring, free): Cloud Run's built-in metrics (requests, latency, 5xx rate, instance count and how often it sits at the max of 1, memory, billable time, cold-start time); app metrics from the structured logs (rooms and connections active, games started and finished, reconnects, WebSocket close codes, snapshot write time and conflicts, rate-limit hits); Neon's console for compute hours, storage and wake-ups; error tracking for both sides (for example Sentry's free tier); an uptime check; and alerts on 5xx rate, sustained max instances and budget. Managed in Terraform.
- Multiple API instances (shared room state through Postgres LISTEN/NOTIFY or Redis) if usage ever outgrows one instance
- Scheduled database export if the Neon 6-hour restore window is not enough

---
