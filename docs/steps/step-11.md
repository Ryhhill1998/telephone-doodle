> Suggested reading (in docs/plan/): 01-product-spec.md; 03-architecture.md; 04-ui-design-brief.md

### Step 11. Reveal and finished screen

Branch `feat/reveal`.

- **Reveal:** shows "<owner>'s book" and "Book b of N", the page's author with a verb ("Chose the word", "Drew it", "Guessed"), the content (the word card, a guess note or `StrokeView`), page dots and "Page p of N+1". The host has Back / Next page buttons (and keyboard arrows), and "Next book" on the last page of a book (it becomes "Finish game" on the last book). Every other player sees a short "<host> is turning the pages" message instead of buttons and follows the pointer automatically. Make it scale well on tablet and large screens.
- **Finished screen:** "That's a wrap!", the row of book tiles and "Play again" (new room). No link and no archive page.
- **Frontend tests:** the reveal for the host (Back disabled on the first step, Next page, "Next book", "Finish game" on the last book, arrow keys send the right messages) and for a non-host (no buttons, follows the pointer in the state), the word card and page rendering for each step kind, and the finished screen ("Play again" creates a new room).

**Review checklist:** with 3 tabs, the host's Next moves every tab together; refreshing a non-host tab mid-reveal returns to the current page; the finished game is in the database with names, words and pages.

---
