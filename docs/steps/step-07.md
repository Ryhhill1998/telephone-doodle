> Suggested reading (in docs/plan/): 04-ui-design-brief.md

### Step 7. Design review gate (me, then Claude Code)

No PR until I approve.

1. I will review the interactive prototype of the screens in section 4 (**https://claude.ai/artifact/M7Wh9dZHav7oH6aMPWqgHY**, private to me) and send change requests. **Do not start any frontend step until I say "design approved".** Backend steps do not wait for this.
2. When I approve, I will export the prototype from the design tool and give you the files (or tell you where they are). Commit them to `frontend/design/` on branch `docs/design-reference` (screenshots and the exported HTML, plus a short `README.md` listing which export is which), and open a PR.
3. From then on, `frontend/design/` plus section 4 is the visual source of truth. If a screen needed in the build is missing from the prototype (for example the Reconnecting banner, the Draw screen in later rounds, or a wide-screen reveal), propose the design in the PR description before building it.

---
