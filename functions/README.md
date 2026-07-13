# Firebase Cloud Functions

This independent Python 3.14 project exports one HTTP function, `dad_joke`, from `main.py`. Firebase deploys it to
`europe-west4` with the `python314` runtime configured in the repository `firebase.json`.

## Endpoint contract

`dad_joke` generates a family-friendly joke through Genkit and Vertex AI. The optional `topic` query parameter accepts:

- `work`
- `tech`
- `food`
- `relationships`

Example response:

```json
{
  "setup": "Why did the developer go broke?",
  "punchline": "Because they used up all their cache.",
  "topic": "tech",
  "style": "pun"
}
```

An invalid topic returns 400. Genkit or Vertex AI failures return 503, and unexpected failures return a generic 500.
The function is configured for 512 MiB memory. Its `TIMEOUT_SEC`, `MIN_INSTANCES`, and `MAX_INSTANCES` parameters
default to 120, 0, and 2 respectively.

## Vertex AI requirements

Enable `aiplatform.googleapis.com` and grant the Functions runtime service account `roles/aiplatform.user`. The model
and Vertex AI location are configured in `main.py`; verify preview-model availability and quotas before deployment.

The function exports Genkit traces and metrics to Google Cloud outside local development. Do not include prompts,
generated content, credentials, or other sensitive values in additional logs.

## Dependency management

Use the repository root commands for the locked development environment:

```bash
just install-functions
just typing-functions
just lint
```

`functions/pyproject.toml` and `functions/uv.lock` define the local environment. Firebase's Python deployment discovers
dependencies through `functions/requirements.txt`, so keep the direct runtime requirements mirrored there whenever
`pyproject.toml` changes. `just update` refreshes both the root and Functions lockfiles.

## Run with the Functions emulator

Create the Firebase-compatible `venv`, then start the Functions emulator from the repository root:

```bash
uv venv --python 3.14 functions/venv
uv pip install --python functions/venv/bin/python -r functions/requirements.txt
export FUNCTIONS_DISCOVERY_TIMEOUT=30
firebase emulators:start --only functions --project PROJECT_ID
```

Call the function on the port configured in `firebase.json`:

```bash
curl "http://127.0.0.1:7020/PROJECT_ID/europe-west4/dad_joke"
curl "http://127.0.0.1:7020/PROJECT_ID/europe-west4/dad_joke?topic=tech"
```

Only the HTTP wrapper runs locally. Joke generation still calls Vertex AI, so the emulator requires network access,
Application Default Credentials, the enabled Vertex AI API, IAM permission, and quota. It is not an offline test double.

## Deploy

```bash
cd functions
uv venv --python 3.14 venv
uv pip install --python venv/bin/python -r requirements.txt
export FUNCTIONS_DISCOVERY_TIMEOUT=30
firebase deploy --only functions --project PROJECT_ID
```

Smoke-test the deployed endpoint:

```bash
curl "https://europe-west4-PROJECT_ID.cloudfunctions.net/dad_joke?topic=relationships"
```

See [GCP.md](../GCP.md) for APIs, IAM, FastAPI deployment, observability, security, and troubleshooting guidance.
