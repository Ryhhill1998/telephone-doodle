> Suggested reading (in docs/plan/): 02-locked-decisions.md; 06-hosting-notes.md

### Step 15. Bootstrap: apply infrastructure and create the Neon database

Branch `docs/infra-bootstrap` (docs and small fixes only; the steps below are actions, not code). There are exactly three manual items; everything else is Terraform.

1. **State bucket (manual, ask first).** Create the Terraform state bucket in the GCP project (versioning on, private, uniform access). Add the backend config to Terraform.
2. **Terraform apply.** Run `terraform plan`, show me the summary, wait for approval, then `terraform apply`.
3. **Neon project (manual, by me).** I create the Neon project myself in the Neon console: region AWS `eu-west-2` (London), the latest available Postgres version, a database `doodle` and a role for the app. Neon is created by hand (not Terraform) on purpose: the community provider is unofficial, and a Terraform mistake must never be able to delete the database. Claude Code gives me the exact steps, including how to copy the **pooled** connection string. Neon's auto-suspend after 5 minutes is fixed on the free plan.
4. **Secret value (manual, by me).** I add the connection string to Secret Manager without it appearing in chat or shell history: `gcloud secrets versions add <secret-name> --data-file=-` and paste when prompted (Claude Code gives me the exact command). Then Claude Code verifies that the secret has a version, without reading it.
5. **GitHub configuration.** Claude Code sets, with `gh variable set` (not secret, none of these are sensitive): the GCP project id, region, Artifact Registry path, Cloud Run service name, deploy service account email, Workload Identity provider name, and `VITE_API_URL` (the Cloud Run URL). Then redeploy the Cloud Run service once so `ALLOWED_ORIGINS` matches the Hosting URL.
6. Document the whole bootstrap in `infrastructure/README.md` (including how to tear down with `terraform destroy`, which leaves the Neon project alone).

**Review checklist:** `terraform plan` shows no changes after apply; the secret has a version; the placeholder Cloud Run service answers on its URL.

---
