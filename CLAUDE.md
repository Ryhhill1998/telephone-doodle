# Telephone Doodle

The build plan is split into small files. Work through the steps one at a time, in order, following the working agreement.

## Start of every session: read only these
1. `docs/PROGRESS.md`
2. `docs/plan/00-working-agreement.md`
3. The one step file the user names (`docs/steps/step-NN.md`), plus the "Suggested reading" files it lists from `docs/plan/`

Do not read `docs/archive/` unless asked. For code that already exists, read the code, not plan text.

## Deviations (working agreement rule 13)
Only if a step is built differently from its step file, edit that step file in the same PR to match. No separate log.

## Keeping cost down (every turn re-reads the whole context)
- Be terse: no narration between tool calls, no recaps. Keep PR descriptions short.
- Use Grep and line ranges; don't read whole large files or re-read a file you just edited.
- While iterating, run the narrowest check (`-q -x`, one file or `-k`). Run full `make lint` and `make test` once before the PR.
- Keep tool output small (`-q`, `--tb=short`, `| tail -n 30`). Never print lockfiles or long logs.
- No subagents, web searches or `/claude-api` unless the step says so or the user asks.
- If context passes about 100k tokens, say so.

## End of every step
Update `docs/PROGRESS.md`: tick the step and add at most 5 lines under "What exists".
