## 8. Definition of done for v0

- [ ] Repo in my personal GitHub account, with all steps merged via reviewed PRs
- [ ] CI green on `main`; latest stable versions in use throughout (versions listed in the README)
- [ ] I approved the UI design before the frontend was built, and the exports live in `frontend/design/`
- [ ] UI live on Firebase Hosting and API live on Cloud Run, each deployed automatically from `main` by its own pipeline, with rollback documented
- [ ] A 3 to 10 player game plays from word pick and drawing to reveal on phones, with reconnect and skip-player working
- [ ] Seat order is a consistent circle, the host can shuffle it and remove players in the lobby, and no two players are dealt the same word
- [ ] Drawings include a working fill tool; an in-progress drawing survives a refresh, a locked phone and a deploy
- [ ] Backend, frontend and Playwright end-to-end tests all exist and pass; CI runs only the jobs for the changed areas, with `ci-ok` as the one required check
- [ ] In the reveal, the host's taps move every player's screen together
- [ ] A deploy, a restart or a scale-to-zero during a game does not end it
- [ ] Rate limits and connection caps in place; budget alerts at $1 and $5 confirmed working
- [ ] Finished games are saved with player names, words and pages
- [ ] Infrastructure managed by Terraform (except the state bucket, the Neon project and the secret value), with a documented teardown
- [ ] README explains how to run, deploy and recover

---
