# Firebase Cloud Functions

This independent Python 3.14 project exports one HTTP function, `dad_joke`, from `main.py`. Firebase deploys it to
`europe-west4` with the `python314` runtime configured in the repository `firebase.json`.

## Endpoint contract

`dad_joke` is a private, GET-only function that generates a family-friendly joke through Genkit and Vertex AI. The
optional `topic` query parameter accepts:

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

Other HTTP methods return 405 without invoking the model. An invalid topic returns 400. Genkit or Vertex AI failures
return 503, and unexpected failures return a generic 500.
The function is configured for 512 MiB memory. Its `TIMEOUT_SEC`, `MIN_INSTANCES`, and `MAX_INSTANCES` parameters
default to 120, 0, and 2 respectively.

## Vertex AI requirements

Enable `aiplatform.googleapis.com`, `logging.googleapis.com`, `cloudtrace.googleapis.com`, and
`monitoring.googleapis.com`. Grant the Functions runtime service account `roles/aiplatform.user`,
`roles/logging.logWriter`, `roles/cloudtrace.agent`, and `roles/monitoring.metricWriter`. The Function deploys in
`europe-west4`, while `main.py` configures the Vertex AI client to use the `global` endpoint and the auto-updating
`gemini-pro-latest` alias. The installed Genkit Vertex AI plugin resolves this alias dynamically.

The alias follows Google's current Gemini Pro model and avoids outages caused by a dated model ID being retired. It is
not a reproducibility pin: behavior, latency, and cost can change without a Function deployment. The response schema
still validates output shape, but it cannot guarantee unchanged semantic quality. Keep the Function private, retain the
contract tests, monitor errors, latency, and spend, and verify alias availability and quota before deployment. See the
[Genkit Python model documentation](https://genkit.dev/docs/python/models/) and
[Python Vertex AI plugin documentation](https://genkit.dev/docs/python/integrations/vertex-ai/).

The function exports Genkit logs, traces, and metrics to Google Cloud outside local development. The telemetry
integration keeps its default input/output redaction. Do not include prompts, generated content, credentials, or other
sensitive values in additional logs.

## Dependency management

Use the repository root commands for the locked development environment:

```bash
just install-functions
just typing-functions
just test-functions
just lint
```

`functions/pyproject.toml` and `functions/uv.lock` define the local environment. Firebase's Python deployment discovers
dependencies through the intentionally lean `functions/requirements.txt`. It pins only the direct runtime packages to
versions from `functions/uv.lock`; Firebase resolves transitive dependencies during deployment. `just update` refreshes
both lockfiles and regenerates the file through a restricted `uv export`. When adding or removing a direct dependency,
update the exporter package list in `Justfile`, then run `just sync-functions-requirements`.
`just check-functions-requirements` verifies the file has not drifted or expanded into an unrestricted export.

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

The function is deployed with private IAM invocation. Grant an intended principal `roles/run.invoker` on the backing
Cloud Run service, then smoke-test with an identity token:

```bash
gcloud run services add-iam-policy-binding FUNCTION_SERVICE \
  --region europe-west4 \
  --member="user:ENGINEER@example.com" \
  --role="roles/run.invoker"

curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "FUNCTION_URL?topic=relationships"
```

Cloud Run functions v2 uses the Cloud Run Invoker role and requires callers to provide an ID token. See
[Authenticate for invocation](https://cloud.google.com/functions/docs/securing/authenticating).

See [GCP.md](../GCP.md) for APIs, IAM, FastAPI deployment, observability, security, and troubleshooting guidance.
