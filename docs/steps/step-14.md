> Suggested reading (in docs/plan/): 02-locked-decisions.md; 03-architecture.md; 06-hosting-notes.md

### Step 14. Terraform for GCP

Branch `infra/terraform`.

First, **ask me for**: the billing account id and its currency, and my Google account email (for budget alert emails). This is the first step where `gcloud` is used, and only for Terraform authentication (`gcloud auth application-default login`, which I run myself).

- All Terraform files sit directly in `infrastructure/`, split as in section 2. Remote state in a GCS bucket (created in Step 15). Latest provider versions (`google` and `google-beta`).
- `apis.tf`: enable Cloud Run, Artifact Registry, Secret Manager, IAM credentials, Security Token Service, Firebase, Firebase Hosting and Billing Budgets APIs.
- `registry.tf`: Artifact Registry Docker repository in `europe-west2`, with a **cleanup policy that keeps only the 3 most recent images** and deletes older ones.
- `iam.tf`: a runtime service account for Cloud Run (only `secretmanager.secretAccessor` on the one secret); a deploy service account for GitHub Actions with the minimum roles (push to the registry, deploy to Cloud Run, act as the runtime service account, deploy Firebase Hosting); **Workload Identity Federation** pool and provider for GitHub with a condition restricting it to my repo, and nothing else, so no service account keys are created anywhere.
- `secrets.tf`: the Secret Manager secret for the Neon connection string, **without a version**. I add the value by hand in Step 15. Use `prevent_destroy` on it.
- `cloud_run.tf`: the API service in `europe-west2`: 1 vCPU, 512 MiB, **`max-instances=1`, `min-instances=0`, concurrency 250, request timeout 3600 s**, request-based billing, startup probe on `/healthz`, public invoker (`allUsers`), env vars `ALLOWED_ORIGINS`, `DATABASE_URL` from the secret, and the rate-limit settings. The container image is set to a placeholder (for example Google's hello image) with `lifecycle { ignore_changes = [template[0].containers[0].image] }`, because GitHub Actions deploys the real image.
- `hosting.tf`: the Firebase project (on the existing GCP project) and the Hosting site.
- `budget.tf`: a monthly budget of $5 (in the billing account's currency) with email alerts at 20% ($1) and 100% ($5), plus a forecasted-100% alert.
- `outputs.tf`: the Cloud Run URL, the Hosting URL, the Artifact Registry path, the deploy service account email and the Workload Identity provider name.

**Review checklist:** `terraform fmt -check` and `terraform validate` pass; `terraform plan` output summarised in the PR, including the expected monthly cost (about $0). **Do not apply yet.**

---
