# Telephone Doodle

The build plan is split into small files. Work through the steps one at a time, in order, following the working agreement.

## Start of every session: read only these
1. `docs/PROGRESS.md`
2. `docs/plan/00-working-agreement.md`
3. The one step file the user names (`docs/steps/step-NN.md`), plus the "Suggested reading" files it lists from `docs/plan/`

## Deviations (working agreement rule 13)
Only if a step is built differently from its step file, edit that step file in the same PR to match. No separate log.

## Keeping cost down (every turn re-reads the whole context)
- Be terse: no narration between tool calls, no recaps. Keep PR descriptions short.
- Use Grep and line ranges; don't read whole large files or re-read a file you just edited.
- Never print lockfiles or long logs.
- Do only what the step lists: no extra tests, no coverage chasing, no deliberately breaking things to prove a test fails, no extra docs.
- No subagents, web searches or `/claude-api` unless the step says so or the user asks.
- If context passes about 100k tokens, say so.

## Run checks yourself
Run lint, tests and builds yourself using the make targets and fix any failures yourself without asking me. Never guess or predict what errors might occur; run the check and read the real output. While iterating run the narrowest check with quiet output (for example `-q -x --tb=short`, `| tail -n 30`). Run the full `make lint` and `make test` once before opening the PR. Do not run terraform, gcloud, firebase or any cloud or deploy command; give me the exact command instead and I'll run it and paste the result.

## No code in the terminal
Never paste file contents, diffs or code blocks into a chat response. The user reviews every change in GitHub (comparing branches/PRs), not in the terminal, and will not read code shown there. Terminal responses are prose only: what changed, why, which files, and the PR/commit link. This doesn't change what you do with Read/Edit/Write/git — only what you print back to the user.

## Keep `.claude/progress.json` live, not just at the end
See the `progress-statusline-and-pr-alert` memory for the full contract. The short version: rewrite `step`, `percent` and `note` as the work actually moves, not only once at the start and once at the end of a step — a stale 100%/`ready` left over from the previous step looks identical to real work being stuck. At the start of a new step, reset it immediately (low `percent`, `state: "working"`) before doing anything else.

## End of every step
Update `docs/PROGRESS.md`: tick the step and add at most 5 lines under "What exists".
