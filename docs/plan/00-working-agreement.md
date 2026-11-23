# BUILD_PLAN.md: Telephone Doodle (v0), revision 5

A web app for playing "telephone pictionary" with family. Each player starts a "book" by picking a word and drawing it. Books are then passed around and players alternate between writing a guess for the previous drawing and drawing the previous guess. At the end, every book is revealed page by page.

---

## 0. Working agreement (applies to every step)

1. **One step = one branch.** A step may be **more than one PR** where that gives a cleaner split (see rule 3). Branch names are `<type>/<short-name>` with no step numbers (types: `feat`, `chore`, `infra`, `ci`, `docs`, `fix`), for example `feat/game-engine`, `chore/scaffold`, `infra/terraform`. Always branch from an up-to-date `main`. Open the PR with `gh pr create`; the description contains: what changed, how to review it, how to run it, and anything deferred.
   **Commit in small, logically ordered steps.** A PR is read commit by commit, so commit at each natural checkpoint as the work happens rather than squashing a step into one large commit. Plan the commit sequence before starting (for example: models, then rotation, then dealing, then serialisation, then tests) and say what it is in the PR description.
2. **Stop after each PR.** Summarise the PR in a few lines and wait for me to say "merged" or "go" before starting the next step. Never merge PRs yourself and never start the next step on an unmerged branch.
3. **Split PRs by logical unit, not by line count.** There is no fixed line budget. Divide a step where the *meaning* divides: data separately from the logic that consumes it (the word bank is its own PR, separate from the game engine), a standalone component separately from the screens that use it, a pure module separately from its wiring. Propose the split up front, say which PR each piece lands in, and keep every PR independently reviewable and green.
4. **Tests are part of the step.** Each step lists acceptance checks. Run them and report the results honestly, including failures.
5. **Never commit secrets** (tokens, keys, connection strings, `.tfvars` with real values, `.env`). Add them to `.gitignore` before they exist. Never print secret values in chat.
6. **Ask before anything that costs money or is hard to reverse.** For Terraform, always run `terraform plan`, show me the summary, and wait for explicit approval before `terraform apply`. Don't create cloud resources outside Terraform, except the three manual items in Step 15 (the Terraform state bucket, the Neon project, and the database secret's value).
7. **Don't enter passwords or tokens on my behalf.** If a login or credential is needed (`gh auth login`, `gcloud auth login`, the Neon connection string), tell me the exact command or page and wait for me to do it.
8. **Don't run `gcloud` or any cloud CLI until Step 14 (Terraform)**, and then only as that step says.
9. **Always use the latest stable versions** of languages, runtimes, libraries, GitHub Actions and base images (see section 2). Never pin versions from memory: let the package manager resolve the latest, look up the current stable release of anything you install or reference by hand, and tell me the versions you ended up with in each PR. If a dependency does not yet support the newest language version, use the newest version it does support and tell me why.
10. **Prefer boring and simple.** No extra frameworks, queues, caches, ORMs or auth systems. If something in this plan seems wrong or over-complicated, say so rather than silently deviating.
11. **One command per check.** Every lint, test, build and check is a `make` target (see Step 1), and CI calls those same targets. Never duplicate a command's flags between the Makefile and a workflow file.
12. **Tests ship with the code they cover**, on both sides: backend with `pytest`, frontend with `vitest` and Testing Library, and a Playwright end-to-end suite (Step 12). A frontend PR without tests is incomplete.
13. **Keep the plan true.** If a step is built differently from how its step file (`docs/steps/step-NN.md`) describes it, or a sub-step is deferred, reordered or dropped, update that step file in the same PR so it matches what was actually done. There is no separate log. Mentioning a deviation only in chat or in a PR description is not enough.

---
