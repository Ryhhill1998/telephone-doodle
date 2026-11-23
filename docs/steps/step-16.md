> Suggested reading (in docs/plan/): 02-locked-decisions.md; 03-architecture.md

### Step 16. CD pipelines

Branch `ci/deploy`.

- **`deploy-api.yml`**: triggers on pushes to `main` that change `backend/**` or the workflow itself (and manually). Steps: authenticate with Workload Identity Federation (`google-github-actions/auth`, latest), build the image with Buildx and push it to Artifact Registry tagged with the commit SHA, deploy a new revision with `--no-traffic --tag candidate`, then call `https://candidate---<service>-<hash>.europe-west2.run.app/healthz` until it passes (fail the job and leave traffic untouched if it doesn't), then shift 100% of traffic to the new revision. **Rollback:** record the previous revision before the switch; if a final health check on the live URL fails, move traffic back to it. Use `concurrency: deploy-api` so deploys never overlap.
- **`deploy-frontend.yml`**: triggers on pushes to `main` that change `frontend/**` (and manually). Install, build with `VITE_API_URL` from the repo variable, and run `firebase deploy --only hosting` authenticated through the same Workload Identity Federation (latest `firebase-tools`). Firebase keeps previous releases, so rollback is one command; document it.
- **Deploys during a game:** Cloud Run sends SIGTERM to the old revision after traffic shifts; the old instance closes sockets with 1012, players reconnect to the new revision, and the room loads from the database. Document this and test it by deploying during a game.
- Terraform changes are applied by me from my machine with plan and approval, not by CI. Say so in the README.

**Review checklist:** merging an API change deploys only the API and a UI change deploys only the UI; the live site works from the Hosting URL; a deploy during a game resumes after a few seconds of reconnecting.

---
