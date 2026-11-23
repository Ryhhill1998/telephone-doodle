## 1. Product spec (v0)

**Players:** 3 to 10, all online at the same time on phones, tablets or laptops. Phone and tablet first.

**Flow**

1. One player creates a room and gets a 4-letter code. Others join with the code and a display name. The creator is the host.
2. Before starting, the lobby shows the players in **seat order** (join order by default), numbered 1 to N. The host can **shuffle the order** with a button (as often as they like) and can **remove a player** (for example a stranger who joined by mistake, or someone who has to leave). Removed players are disconnected and see a "You were removed" message. The host starts the game (min 3 players; no joining after start). Starting freezes the seat order.
3. With `N` players there are `N` books and `N` rounds (`r = 0 .. N-1`). The seats form a **circle**: seat 1 follows seat N. Each round every book moves on to the next seat in the circle, so player in seat `p` works on book `(p - r) mod N` (their own book in round 0; the book of the seat before them in round 1; and so on). The direction and order never change during a game, so the passing is always predictable from the lobby list.
   - **Round 0 (pick and draw):** the player gets 3 random words from the word bank and picks one, **or** types their own (they can shuffle to get 3 new words). **Dealt words never repeat across players:** all players' options are drawn from one shuffled bank without replacement, and a shuffle draws from the words not yet dealt or picked. Typed words are deliberately **not** compared with other players' words, because any such check would reveal what someone else picked; only dealt words are guaranteed unique. They then **draw that word** on the next screen. The chosen word is stored privately on the book and is only shown at the reveal. The drawing is page 1 of their own book.
   - **Odd rounds (guess):** the player sees only the previous page (a drawing) and writes what they think it is.
   - **Even rounds >= 2 (draw):** the player sees only the previous page (a guess) and draws it.
   - With an odd number of players the last page of every book is a drawing that nobody guesses. That is fine for v0.
4. A round ends when **every player has submitted** ("ready-based"). There is no timer in v0. The UI shows who has finished.
5. After the last round, the **reveal** begins. For each book, the host steps through it: first a **word card** (who chose the word and what it was), then each page in order, with its author's name. Drawings are rendered statically from stroke data (replay animation is v1). After the last page of a book the host taps "Next book"; after the last book they finish the game.
6. **Everyone sees the same reveal screen at the same time:** the host's taps move a shared pointer on the server and every player's screen follows (see "Reveal sync" in section 3). Other players do not get Back or Next buttons.
7. When the host finishes, the game is marked finished and everyone sees a "That's a wrap" screen with a "Play again" button. There is **no shareable link or archive page** in v0.

**What we store:** only display names and the game's content (each book's starting word, the pages, who made each). There are **no accounts, passwords, emails or per-player stats**. Player tokens exist only while a game is in progress and are removed when it finishes. Finished games are kept quietly in the database so that v1 features (a highlights reel, voting on funniest books, scoring) have data to work with, but v0 has no screen that reads them back.

**Out of scope for v0 (do not build):** scoring, fuzzy matching, timers, votes or reactions, highlights, awards, accounts or auth, async play, stroke replay animation, themed word packs, permalinks or an archive page, browsing past games, running more than one API instance.

**Robustness requirements (in scope):**
- Players get a random token on join, stored in `localStorage`. Refreshing the page, locking the phone or closing the tab must **rejoin the same seat**: the home page shows a "Rejoin room KQFM" button while a saved seat exists, and the app reconnects automatically when the tab becomes visible or the network returns.
- **Drafts survive interruptions.** A drawing in progress (and a half-typed guess) is saved to `localStorage` after every stroke, keyed by room code and round, and restored when the same player returns to the same round on the same device (after a refresh, a locked phone, an accidental exit, or a server deploy that drops the socket). It is cleared when the page is submitted. Drafts are not synced between devices.
- If a player is disconnected during a round, the game waits. The host gets a "Skip" button which submits a blank page for that player.
- A player must never receive other players' pages or words before the reveal. The server only sends each player what they're allowed to see.
- **Games survive server restarts, deploys and scale-to-zero** (see Step 5): in-progress games are saved to Postgres on every change and loaded back on demand, and clients reconnect automatically.
- Games abandoned for 24 hours are deleted from the database; empty rooms are dropped from memory after about 6 hours of inactivity.
- **Abuse protection** (see Step 6): per-IP rate limits and connection caps, so a public URL can't be used to run up costs.

---
