## 6. Hosting notes (for explaining things to me)

- **Cloud Run** runs the API container only when needed and scales to zero when nobody is connected. It gives the service an HTTPS `*.run.app` URL, so there are no certificates or domain names to manage. We cap it at one instance, so cost is bounded. It supports WebSockets, and a connection counts as an active request while it is open.
- **Neon** is serverless Postgres. On the free plan the database compute sleeps after 5 minutes idle and wakes in about a second. If a monthly limit is hit, compute is suspended until the next month rather than billed.
- **Firebase Hosting** serves the built React files from a global CDN. It is free at our scale and deploys in seconds.
- **Artifact Registry** is GCP's container image store (like ECR). A cleanup policy keeps it at about zero cost.
- **Workload Identity Federation** lets GitHub Actions prove who it is to GCP using a short-lived token, so there are no downloaded keys to leak or rotate.
- **Budget alerts** email me at $1 and $5 a month. They do not stop spending by themselves; `max-instances=1`, rate limits and Neon's no-overage behaviour are what keep the worst case small.

---
