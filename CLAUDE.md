# Telephone Doodle

The build plan is split into small files. Work through the steps one at a time, in order, following the working agreement.

## Start of every session: read only these
1. `docs/PROGRESS.md`
2. `docs/plan/00-working-agreement.md`
3. The one step file the user names (`docs/steps/step-NN.md`), plus the "Suggested reading" files it lists from `docs/plan/`

## Deviations (working agreement rule 13)
Only if a step is built differently from its step file, edit that step file in the same PR to match. No separate log.

## Only do what's explicitly asked
A message that directly instructs you to implement/build/fix/add something means implement it. A message asking for a plan, an idea, options, or anything else that isn't a direct instruction to do work means respond only — do not write, edit, commit or push until given explicit go-ahead.

When you do implement:
- Change to an existing PR: implement, commit, and push to the current branch.
- Work from scratch (no PR yet): commit in small, logically ordered chunks, push, and open a PR with a short, concise description — no essays.

## Run checks yourself
Run lint, tests, builds and installs yourself whenever you actually need to verify something — don't run them speculatively or after every small change, and never guess or predict what an error might be; run the real check and read the real output. Use the narrowest check while iterating (one file, `-k`, `-x`, quiet flags, e.g. `-q -x --tb=short | tail -n 30`), and run the full `make lint` and `make test` once before opening the PR. Never print lockfiles or long logs. Terraform, gcloud, firebase and any other cloud or deploy command are not yours to run — give the exact command instead and the user will run it and paste back the result. File reading, editing and writing, and git and `gh` (branch, commit, push, open PR) are yours to do.

## Keeping cost down (every turn re-reads the whole context)
- Be terse: no narration between tool calls, no recaps. Keep PR descriptions short.
- Use Grep and line ranges; don't read whole large files or re-read a file you just edited.
- Do only what the step lists: no extra tests, no coverage chasing, no deliberately breaking things to prove a test fails, no extra docs.
- No subagents, web searches or `/claude-api` unless the step says so or the user asks.
- If context passes about 100k tokens, say so.

## Use the library's documented pattern
When a library or framework has a standard, documented way to do something (e.g. FastAPI's cached-settings-plus-`Depends` pattern), use that instead of inventing a bespoke one. If no documented pattern fits, say so and propose an alternative rather than silently making one up.

## No code in the terminal
Never paste file contents, diffs or code blocks into a chat response. The user reviews every change in GitHub (comparing branches/PRs), not in the terminal, and will not read code shown there. Terminal responses are prose only: what changed, why, which files, and the PR/commit link. This doesn't change what you do with Read/Edit/Write/git — only what you print back to the user.

## Keep `.claude/progress.json` live, not just at the end
See the `progress-statusline-and-pr-alert` memory for the full contract. The short version: rewrite `step`, `percent` and `note` as the work actually moves, not only once at the start and once at the end of a step — a stale 100%/`ready` left over from the previous step looks identical to real work being stuck. At the start of a new step, reset it immediately (low `percent`, `state: "working"`) before doing anything else.

## End of every step
Update `docs/PROGRESS.md`: tick the step and add at most 5 lines under "What exists".
