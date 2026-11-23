> Suggested reading (in docs/plan/): 07-v1-backlog.md; 08-definition-of-done.md

### Step 17. Live verification and docs

Branch `docs/wrapup`.

- Play a full game against the live Hosting URL using at least 3 devices or tabs, including a phone, and report what happened (including any rough edges: cold start time, Neon wake-up time).
- Check the Cloud Run and Neon usage pages and the budget page after the test game, and report the numbers so I can see how far a game moves them.
- Write a real `README.md`: what the game is, how to play, local dev setup, architecture overview (including the two-origin setup, the package dependency direction, reveal sync and load-on-demand rooms), deploy and rollback for both pipelines, cost and limits, known limitations, and the v1 roadmap below.
- Add a short `docs/PLAYTEST.md` checklist (rejoin after refresh, skip player, odd and even player counts, long text, big drawings, slow network, scale-to-zero while phones are locked, deploy during a game, reveal on several devices).

**Review checklist:** I can play a family game on my phone from the live URL.

---
