# Firebase Cloud Functions

Run these commands to deploy:

```bash
cd functions
uv sync
export FUNCTIONS_DISCOVERY_TIMEOUT=30
firebase deploy --only functions
```

For a detailed, end-to-end infrastructure and IAM setup (APIs, roles, environment variables, Cloud Build integration, Functions vs Cloud Run guidance) see: [`GCP.md`](../GCP.md).
