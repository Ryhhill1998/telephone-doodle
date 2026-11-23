# Telephone Doodle

The build plan is split into small files. Work through the steps one at a time, in order, following the working agreement.

## Start of every session: read only these
1. `docs/PROGRESS.md`
2. `docs/plan/00-working-agreement.md`
3. The one step file the user names (`docs/steps/step-NN.md`), plus the "Suggested reading" files it lists from `docs/plan/`

## Deviations (working agreement rule 13)
Only if a step is built differently from its step file, edit that step file in the same PR to match. No separate log.

## The user runs the commands (to keep cost down)
Do not run tests, lint, builds, installs, Docker, Terraform or any cloud command yourself. Write the code, then give the user the exact command(s) to run (for example `make lint && make test`). The user runs them and pastes back only the failures. Fix, then give the command again. File reading, editing and writing, and git and `gh` (branch, commit, push, open PR) are yours to do.

## Keeping cost down (every turn re-reads the whole context)
- Be terse: no narration between tool calls, no recaps. Keep PR descriptions short.
- Use Grep and line ranges; don't read whole large files or re-read a file you just edited.
- Suggest the narrowest check while iterating (`-q -x`, one file or `-k`), and the full `make lint` and `make test` once before the PR.
- Never print lockfiles or long logs.
- Do only what the step lists: no extra tests, no coverage chasing, no deliberately breaking things to prove a test fails, no extra docs.
- No subagents, web searches or `/claude-api` unless the step says so or the user asks.
- If context passes about 100k tokens, say so.

## No code in the terminal
Never paste file contents, diffs or code blocks into a chat response. The user reviews every change in GitHub (comparing branches/PRs), not in the terminal, and will not read code shown there. Terminal responses are prose only: what changed, why, which files, and the PR/commit link. This doesn't change what you do with Read/Edit/Write/git — only what you print back to the user.

## Keep `.claude/progress.json` live, not just at the end
See the `progress-statusline-and-pr-alert` memory for the full contract. The short version: rewrite `step`, `percent` and `note` as the work actually moves, not only once at the start and once at the end of a step — a stale 100%/`ready` left over from the previous step looks identical to real work being stuck. At the start of a new step, reset it immediately (low `percent`, `state: "working"`) before doing anything else.

## End of every step
Update `docs/PROGRESS.md`: tick the step and add at most 5 lines under "What exists".
