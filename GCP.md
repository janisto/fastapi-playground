# Google Cloud and Firebase setup

This guide covers the two independent deployment targets in this repository:

- the FastAPI container in `app/`, deployed to Cloud Run;
- the Python function in `functions/`, deployed with the Firebase CLI to Cloud Run functions.

Both target Python 3.14. The function runtime is pinned to `python314` in `firebase.json`; Python 3.14 is currently a
supported [Cloud Run functions runtime](https://cloud.google.com/functions/docs/runtime-support#python).

## Project and Firebase products

Use one Google Cloud project linked to Firebase. Configure its project ID as `FIREBASE_PROJECT_ID` for the FastAPI
service and use the same project when running Firebase CLI commands.

Enable only the products used by the deployment target:

- Authentication and Firestore in Native mode for the FastAPI profile API;
- Vertex AI for the `dad_joke` function;
- Cloud Storage for Firebase only if you plan to use the checked-in storage rules.

The repository uses `europe-west4` for Firestore, Functions, and Vertex AI. Storage location is selected when the bucket
is provisioned rather than in `firebase.json`. Choose the Cloud Run service region explicitly when deploying the
FastAPI container.

## APIs and IAM

Enable the relevant APIs for your deployment:

- `run.googleapis.com` for Cloud Run and the function's backing service;
- `cloudfunctions.googleapis.com` for Firebase CLI-managed function deployment;
- `firestore.googleapis.com` for Firestore;
- `aiplatform.googleapis.com` for the Genkit Vertex AI function;
- `artifactregistry.googleapis.com` for the FastAPI image and function build artifacts;
- `cloudbuild.googleapis.com` for Firebase's function source build;
- `logging.googleapis.com` for build and runtime logs;
- `secretmanager.googleapis.com` only when injecting managed secrets.

Grant the runtime service account the minimum roles required by the deployed component:

- FastAPI: `roles/datastore.user` and normally `roles/logging.logWriter`;
- `dad_joke` function: `roles/aiplatform.user` and normally `roles/logging.logWriter`;
- intended `dad_joke` callers: `roles/run.invoker` on the function's backing Cloud Run service;
- Secret Manager consumers: `roles/secretmanager.secretAccessor` for only the required secrets.

Do not grant project-wide `Editor`. Prefer the Cloud Run or Functions runtime service account and Application Default
Credentials. For local development, prefer `gcloud auth application-default login`; use a downloaded service-account
key only when necessary, keep it outside the repository, and point `GOOGLE_APPLICATION_CREDENTIALS` to it.

## Local MCP authentication

The repository configures the Firebase MCP server and the managed Cloud Logging MCP server for both VS Code and
Codex. Firebase uses the credentials available to the Firebase CLI. Cloud Logging uses
`GOOGLE_CLOUD_ACCESS_TOKEN` for OAuth and `GOOGLE_CLOUD_PROJECT` as the `x-goog-user-project` quota project; neither
value belongs in repository configuration.

Keep the gcloud default project and the Application Default Credentials quota project aligned:

```bash
gcloud config set project PROJECT_ID
gcloud auth application-default login
gcloud auth application-default set-quota-project PROJECT_ID
```

For zsh, add the following to `~/.zshrc`:

```bash
export GOOGLE_CLOUD_PROJECT="PROJECT_ID"
export GOOGLE_CLOUD_ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"
```

Run `source ~/.zshrc` and restart VS Code or Codex after changing these values. The access token is short-lived and is
regenerated when a new shell sources `~/.zshrc`; refresh and restart a long-running client when authentication expires.
Never commit the expanded token, and use this convenience setup only on a trusted workstation because child processes
inherit it. If setting the ADC quota project fails, the local identity needs
`serviceusage.services.use`, commonly granted through `roles/serviceusage.serviceUsageConsumer`. See
[Google Cloud MCP authentication](https://docs.cloud.google.com/mcp/authenticate-mcp) for authentication options and
token-refresh limitations.

## FastAPI configuration

These settings are defined in `app/core/config.py`:

| Variable | Required in deployment | Default | Purpose |
|---|---:|---|---|
| `FIREBASE_PROJECT_ID` | Yes | none | Firebase and Firestore project ID |
| `FIRESTORE_DATABASE` | No | `(default)` | Optional named Firestore database |
| `GOOGLE_APPLICATION_CREDENTIALS` | Local only | unset | Explicit credential-file path; omit on Cloud Run |
| `ENVIRONMENT` | No | `production` | `development`, `test`, or `production` |
| `DEBUG` | No | `false` | Debug logging and development behavior |
| `MAX_REQUEST_SIZE_BYTES` | No | `1000000` | Maximum request-body size |
| `CORS_ORIGINS` | Browser clients only | empty | JSON array or comma-separated allowed origins |

`PORT` is consumed by the development and container commands, not by `Settings`; it defaults to `8080`.

Example Cloud Run values:

```dotenv
FIREBASE_PROJECT_ID=your-project-id
ENVIRONMENT=production
DEBUG=false
FIRESTORE_DATABASE=(default)
CORS_ORIGINS=["https://app.example.com"]
```

## Local development and tests

Install and run the FastAPI app from the repository root:

```bash
just install
just serve
```

The API documentation is available at `http://127.0.0.1:8080/api-docs`; `/health` is a dependency-free liveness
endpoint and does not verify Firebase, Firestore, or Vertex AI readiness.

Unit and integration tests mock Auth and Firestore. The E2E profile test overrides authentication but uses the local
Firestore emulator for real transaction behavior:

```bash
# Terminal 1
just emulators

# Terminal 2
just test-e2e
```

The emulator ports come from `firebase.json`: Auth `7010`, Functions `7020`, Firestore `7030`, and Storage `7040`.
`just emulators` intentionally uses the synthetic `demo-test` project so local test data cannot be confused with a
deployed project.
The server-side Firestore client connects through `FIRESTORE_EMULATOR_HOST`; keep the value protocol-free, as
documented by the [Firebase Emulator Suite](https://firebase.google.com/docs/emulator-suite/connect_firestore#admin_sdks).

## FastAPI container

The Dockerfile uses BuildKit cache mounts, installs only runtime dependencies from `uv.lock`, runs as UID/GID 1001,
and starts Uvicorn without duplicate access logging. Cloud Run terminates TLS before proxying cleartext HTTP to the
container, so Uvicorn is configured to trust Cloud Run's forwarded headers. This preserves the original HTTPS scheme
for generated URLs and HSTS decisions; do not remove those runtime flags without verifying `/health`, schema links,
and security headers through the deployed service.

Production deployment is already managed by existing Google Cloud configuration outside this repository. Do not use
local container commands or examples in this guide to replace its build, image, or rollout conventions.

## Deploy the Firebase function

The `dad_joke` HTTP function uses:

- runtime `python314` in `europe-west4`;
- 512 MiB memory and `TIMEOUT_SEC` default `120`;
- `MIN_INSTANCES` default `0` and `MAX_INSTANCES` default `2`;
- Genkit with the Vertex AI model configured in `functions/main.py`;
- GCP trace and metric export outside local development.
- private IAM invocation; unauthenticated internet requests cannot consume model quota.

Firebase deployment uses `functions/requirements.txt`, which is an exact export of the runtime dependency graph in
`functions/uv.lock`. Run `just update` to refresh both and `just check-functions-requirements` to detect drift.

```bash
cd functions
uv venv --python 3.14 venv
uv pip install --python venv/bin/python -r requirements.txt
export FUNCTIONS_DISCOVERY_TIMEOUT=30
firebase deploy --only functions --project PROJECT_ID
```

The deployed function uses Cloud Run functions v2 authentication. Grant only intended principals the Cloud Run
Invoker role on the backing service, then call it with an identity token:

```bash
gcloud run services add-iam-policy-binding FUNCTION_SERVICE \
  --region europe-west4 \
  --member="user:ENGINEER@example.com" \
  --role="roles/run.invoker"

curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "FUNCTION_URL?topic=tech"
```

Cloud Run functions v2 requires both `roles/run.invoker` permission and an ID token for authenticated invocation; see
[Authenticate for invocation](https://cloud.google.com/functions/docs/securing/authenticating).

For local function emulation:

```bash
firebase emulators:start --only functions --project PROJECT_ID
curl "http://127.0.0.1:7020/PROJECT_ID/europe-west4/dad_joke?topic=tech"
```

The emulator runs the HTTP wrapper locally and does not enforce deployed IAM. Generating a joke still calls Vertex AI,
so it requires network access, Application Default Credentials, the Vertex AI API, and `roles/aiplatform.user`; it is
not an offline fake.

See [functions/README.md](functions/README.md) for the endpoint contract and Functions-specific commands. Firebase
uses `requirements.txt` for Python deployments, consistent with the current
[Firebase Functions setup](https://firebase.google.com/docs/functions/get-started).

## Observability and security

The FastAPI service writes structured JSON to stdout. `fastapi-request-observability` adds request IDs, one access
record per request, route metadata, and incoming W3C Trace Context correlation. It does not create spans. The Functions
project separately configures Genkit GCP telemetry.

Production checklist:

- keep `DEBUG=false`;
- terminate TLS at Cloud Run and verify HSTS on HTTPS responses;
- keep the model-backed function private and grant `roles/run.invoker` only to intended callers;
- configure explicit `CORS_ORIGINS` for browser clients;
- inject production secrets from Secret Manager rather than plain values;
- rebuild the custom image regularly for OS, Python, and dependency patches;
- configure log-based alerts and budgets for Vertex AI usage.

## Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| Profile request returns 500 | Firestore configuration or permission failure | Project ID, ADC, database name, and `roles/datastore.user` |
| Auth returns 401 | Missing, expired, revoked, disabled-user, or invalid token | Bearer token and `WWW-Authenticate` response header |
| Auth returns 503 | Firebase verification dependency unavailable | ADC, network access, public-key retrieval, and `Retry-After` |
| Function returns 400 | Unsupported `topic` query value | Use `work`, `tech`, `food`, or `relationships` |
| Function returns 401/403 before handler | Missing identity token or caller IAM | ID token and `roles/run.invoker` on the backing service |
| Function returns 503 | Genkit or Vertex AI failure | Vertex API, region/model availability, ADC, IAM, and quotas |
| E2E test skips | Firestore emulator is not running on `127.0.0.1:7030` | Run `just emulators` |
| CORS is blocked | Origin is absent from `CORS_ORIGINS` | Configure an exact allowed origin |
