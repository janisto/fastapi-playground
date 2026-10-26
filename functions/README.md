# Firebase Cloud Functions

This independent Python 3.15 example exports one HTTP function, `dad_joke`, from `main.py`. It is not deployed.
Future manual Firebase deployment targets `europe-west4` with `python315` in the repository `firebase.json`.
PRs and merges do not deploy it. Isolated tests require no GCP account, ADC, or Vertex AI calls.

The [published Functions runtime table](https://docs.cloud.google.com/functions/docs/runtime-support#python) and
[Firebase CLI 15.34.0 runtime definitions](https://github.com/firebase/firebase-tools/blob/v15.34.0/src/deploy/functions/runtimes/supported/types.ts)
currently stop at Python 3.14. Functions emulation requires CLI recognition of `python315`; deployment also needs
a published platform runtime. Keep the repository's Python 3.15 target and recheck the relevant prerequisites
before running either future workflow below.
The Auth/Firestore emulators used by the FastAPI app are separate and work with `just emulators`.

Commands below run from the repository root unless a snippet explicitly changes directory.

## Endpoint contract

`dad_joke` is a private, GET-only function that generates a family-friendly joke through Genkit and Vertex AI. The
optional `topic` query parameter accepts:

- `work`
- `tech`
- `food`
- `relationships`

Topic matching is case-insensitive; an omitted or empty topic produces `topic: null`. The Function selects a style
randomly from `pun`, `literal`, `homophone`, `anticlimax`, and `misunderstanding`. Repeating a successful GET can
produce a different joke and consume more Vertex AI quota.

Example response:

```json
{
  "setup": "Why did the developer go broke?",
  "punchline": "Because they used up all their cache.",
  "topic": "tech",
  "style": "pun"
}
```

Responses use `application/json`. Errors use `error` and `message` members. Other HTTP methods return 405 with
`Allow: GET` without invoking the model; an invalid topic returns 400. Genkit, Vertex AI, or invalid
model-output failures return a sanitized 503, and unexpected failures return a generic 500. Generated setup and
punchline values must be non-blank strings no longer than 500 characters; missing, non-object, or additional output is
rejected before constructing the public response.
The function is configured for 512 MiB memory and one concurrent request per instance to bound model quota usage. Its
`TIMEOUT_SEC`, `MIN_INSTANCES`, and `MAX_INSTANCES` parameters default to 120, 0, and 2 respectively.

## Vertex AI requirements

Enable `aiplatform.googleapis.com` and `logging.googleapis.com`. Grant the Functions runtime service account
`roles/aiplatform.user`. The Function deploys in `europe-west4`, while `main.py` configures the Vertex AI client to use
the `global` endpoint and the auto-updating `gemini-pro-latest` alias. The installed Genkit Google GenAI integration
resolves this alias dynamically.

The alias follows Google's current Gemini Pro model and avoids outages caused by a dated model ID being retired. It is
not a reproducibility pin: behavior, latency, and cost can change without a Function deployment. The response schema
still validates output shape, but it cannot guarantee unchanged semantic quality. Keep the Function private, retain the
contract tests, monitor errors, latency, and spend, and verify alias availability and quota before deployment. See the
[Genkit Python model documentation](https://genkit.dev/docs/python/models/) and
[Python Vertex AI plugin documentation](https://genkit.dev/docs/python/integrations/vertex-ai/).

In Cloud Run functions, the Function formats Genkit logs as structured JSON on stdout for platform capture. It does not
configure a Genkit trace or metric exporter. Do not include prompts, generated content, credentials, or other sensitive
values in additional logs.

## Dependency management

Use the repository root commands for the independent locked development environment:

```bash
just install-functions   # Sync functions/.venv from functions/uv.lock
just typing-functions    # Check the Function using its environment
just test-functions      # Isolated handler/model/deployment-metadata tests
just qa                  # Complete app and Functions quality gate
```

`functions/.venv` is separate from the application `.venv`. From the root, `just test-all` includes these isolated
Functions tests alongside application tests and the Auth/Firestore E2E suite; keep `just emulators` running for that
suite. `just test-all` does not start the Functions emulator or call Vertex AI.

`functions/pyproject.toml` and `functions/uv.lock` define the local environment. Firebase's Python deployment discovers
dependencies through the intentionally lean `functions/requirements.txt`. It pins only the direct runtime packages to
versions from `functions/uv.lock`; Firebase resolves transitive dependencies during deployment. `just update` refreshes
both lockfiles and regenerates the file through a restricted `uv export`. When adding or removing a direct dependency,
update the exporter package list in `Justfile`, then run `just sync-functions-requirements`.
`just check-functions-requirements` verifies the file has not drifted or expanded into an unrestricted export.

## Run with the Functions emulator

This future workflow waits on Firebase CLI recognition of `python315`. It is distinct from the working FastAPI
Auth/Firestore emulator workflow. The separate `functions/venv` directory is for Firebase CLI discovery and deployment;
ordinary locked development and tests use `functions/.venv`.

After CLI support is available, create that Firebase-compatible environment and start the Functions emulator:

```bash
uv venv --python 3.15 functions/venv
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

This optional manual workflow requires both Firebase CLI and platform Python 3.15 support and a project you control.
Follow [GCP.md](../GCP.md) for project setup, billing, APIs, deployment permissions, and runtime IAM before running
these commands.

```bash
cd functions
uv venv --python 3.15 venv
uv pip install --python venv/bin/python -r requirements.txt
export FUNCTIONS_DISCOVERY_TIMEOUT=30
firebase deploy --only functions --project PROJECT_ID
```

The function is deployed with private IAM invocation. Grant an intended principal `roles/run.invoker` on the backing
Cloud Run service, then smoke-test with an identity token:

```bash
gcloud run services add-iam-policy-binding FUNCTION_SERVICE \
  --project PROJECT_ID \
  --region europe-west4 \
  --member="user:ENGINEER@example.com" \
  --role="roles/run.invoker"

curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "FUNCTION_URL?topic=relationships"
```

Cloud Run functions v2 uses the Cloud Run Invoker role and requires callers to provide an ID token. See
[Authenticate for invocation](https://cloud.google.com/functions/docs/securing/authenticating).

See [GCP.md](../GCP.md) for APIs, IAM, FastAPI deployment, observability, security, and troubleshooting guidance.
