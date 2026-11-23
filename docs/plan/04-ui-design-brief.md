## 4. UI design brief (the visual source of truth until `frontend/design/` exists)

An interactive prototype of these screens has been built for my review: **https://claude.ai/artifact/M7Wh9dZHav7oH6aMPWqgHY** (private to me; it may not open for you). **Do not start any frontend step until I have approved it and given you the exported files** (see Step 7); if you cannot open the link, ask me for the export. Implement the frontend to match it once approved. Tokens:

- **Colours:** paper `#FAF6EE`, ink `#1E2330`, card `#FFFFFF`, line `#E4DCCB`, input border `#8C8676`, muted text `#5E6472`, primary action red `#C8381F` (white text), highlight yellow `#FFD95A`, soft yellow `#FFF1B8`, success green `#1F7A4D`, focus ring blue `#2B59C3`. Avatar fills: `#FFD95A #BFD7FF #FFC9BC #CDEBC8 #E3D4FF`. Brush palette (14 presets plus eraser and a custom-colour swatch): ink `#1E2330`, grey `#8C8676`, brown `#7A4B2A`, red `#C8381F`, pink `#F26B9B`, orange `#F08A24`, yellow `#FFD95A`, lime `#9BD13B`, green `#2E9B5B`, teal `#1FA8A0`, sky blue `#4FB3F0`, blue `#2B59C3`, purple `#7A4FC9`, skin `#F2C9A0`, eraser (white). The custom swatch (a rainbow ring) opens a colour picker.
- **Type:** Space Grotesk 500/700 for headings and the room code, Inter 400/500/600 for body.
- **Shape:** buttons radius 14, cards 20, inputs 12, pills 999. All tap targets at least 44px. Visible `:focus-visible` outline. Respect `prefers-reduced-motion`.
- **Layout:** phone-first at 390px wide; on wider screens centre a column (max about 480px). The reveal screen should also scale up nicely on a tablet or TV.
- **Screens (8):**
  1. Home (name, create room, join with code).
  2. Lobby (big room code with copy, numbered player list in seat order, host-only Shuffle order and remove-player crosses, host Start).
  3. Pick a word (3 options, shuffle, type your own; the button says "Draw it").
  4. Draw (round 1: "Your word, now draw it", with the word on a note; in later rounds the note shows the previous guess; 4:3 canvas, a two-row palette of 14 colours plus eraser and a custom-colour swatch, a **brush-size slider** (2 to 40 on the 800-wide canvas, with a live dot preview), a **fill (bucket) tool**, icon-only undo and clear, done).
  5. Waiting (player list with done, working, disconnected; host Skip; progress bar).
  6. Guess (the previous drawing and a text input).
  7. Reveal (author, verb, page, dots; first step of each book is the word card; the host has Back and Next page / Next book; every other player sees a "Jo is turning the pages" message instead of buttons).
  8. Finished ("That's a wrap!", a row of book tiles, Play again). No link.
- A **"Reconnecting..."** banner is needed on every in-game screen (not in the prototype). Also show a friendly "Waking things up..." message if the first connection takes more than a couple of seconds (Cloud Run and Neon cold starts).

---
