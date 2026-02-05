# Firebase Cloud Functions

Run these commands to deploy:

```bash
cd functions
uv sync
export FUNCTIONS_DISCOVERY_TIMEOUT=30
firebase deploy --only functions
```

For a detailed, end-to-end infrastructure and IAM setup (APIs, roles, environment variables, Cloud Build integration, Functions vs Cloud Run guidance) see: [`GCP.md`](../GCP.md).

# Vertex AI usage and required setup

This project uses Google Cloud Vertex AI (via the VertexAI plugin for Genkit) from Cloud Functions. To allow this:

1. **Enable the Vertex AI API** (`aiplatform.googleapis.com`) in your project:  
   https://console.developers.google.com/apis/api/aiplatform.googleapis.com/overview
2. **Grant the Cloud Functions service account** the `roles/aiplatform.user` role (via IAM in the Cloud Console or `gcloud iam roles`), so that deployed functions can call Vertex AI.
## Run checks from root

```bash
uv run ruff check --fix functions/main.py
uv run ty check --python functions/.venv functions/main.py
```

## Run emulators from root

> **Note**: Firebase emulator doesn't support `python314` runtime yet. Change `runtime` in `firebase.json` to `python313` for local testing, or deploy directly.

```bash
firebase emulators:start --only functions

# Default (no topic)
curl http://127.0.0.1:5001/<PROJECT_ID>/europe-west4/dad_joke

# With topic
curl "http://127.0.0.1:5001/<PROJECT_ID>/europe-west4/dad_joke?topic=tech"
```

## Deploy from root

```bash
firebase deploy --only functions

# Default (no topic)
curl https://europe-west4-<PROJECT_ID>.cloudfunctions.net/dad_joke

# With topic
curl "https://europe-west4-<PROJECT_ID>.cloudfunctions.net/dad_joke?topic=relationships"
```
