> Suggested reading (in docs/plan/): 01-product-spec.md; 03-architecture.md; 04-ui-design-brief.md

### Step 10. Gameplay screens

Branch `feat/gameplay`. Requires Steps 8 and 9.

Wire the UI to the `state` snapshots for rounds, matching the design:

- **Pick a word, then draw it (round 0):** 3 word buttons, a "Shuffle words" button, an "or type your own" input; "Draw it" sends `pick_word` and moves to the Draw screen with the picked word on the note. Both screens are Round 1.
- **Draw (all drawing rounds):** the note shows the word (round 0) or the previous guess (later rounds), the canvas, a "Done" button that sends `submit_page` with strokes.
- **Guess:** shows the previous drawing via `StrokeView`, a text input and a "Done" button.
- **Waiting:** a list of players with done, working or disconnected, a progress bar, and for the host a "Skip" button beside any disconnected, unfinished player.
- Round indicator ("Round 2 of 5") and progress segments, and a clear "you've already submitted" state. After a refresh, a locked phone, an accidental exit or a deploy-triggered reconnect mid-round, the screen restores correctly: the picked word and submitted state come from the server, and the **draft drawing and half-typed guess come back from `localStorage`** (saved after every stroke or keystroke, keyed by room code, round and player, cleared on submit, and expired after 24 hours).
- **Frontend tests:** the word screen (pick, shuffle, type your own, "Draw it" sends `pick_word`), the draw screen (Done sends the operations, draft saved and restored from a pre-filled `localStorage`, cleared after submit), the guess screen (shows only the previous page, submit sends text, draft restore), the waiting screen (statuses, Skip visible only to the host and only for disconnected players), and a "game state to screen" mapping test for every phase.

**Review checklist:** 3 browser tabs can play a full game to the end of the final round; the guess screen never shows anything but the immediately previous page.

---
