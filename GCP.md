# Google Cloud and Firebase setup

This guide preserves optional manual setup for two independent deployment examples:

- the FastAPI container in `app/`, deployable to Cloud Run;
- the Python function in `functions/`, deployable with the Firebase CLI to Cloud Run functions.

The repository has CI only and no maintained deployment or cloud MCP connection. Pushes, PRs, and merges do not deploy
these examples. Follow this guide only with an account and project you control; ordinary local development and
isolated tests require no GCP account. Cloud resource retirement is managed separately from repository maintenance.

Both target Python 3.14. The function runtime is pinned to `python314` in `firebase.json`; Python 3.14 is currently a
supported [Cloud Run functions runtime](https://cloud.google.com/functions/docs/runtime-support#python).

## Project and Firebase products

For a future deployment:

1. Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install), [Firebase CLI](https://firebase.google.com/docs/cli),
   Python 3.14+, `uv`, and `just`.
2. Create or select your own Google Cloud project, link a billing account, and configure budgets and alerts. Firebase
   Functions deployment requires the [Blaze plan](https://firebase.google.com/docs/functions/get-started).
3. Add Firebase to that project in the Firebase console. For the profile API, create a Native-mode Firestore database
   and enable the Authentication sign-in providers your client uses. Obtain a Firebase ID token through that client.
4. Enable the relevant APIs below and configure separate deployment and runtime permissions before deploying.

Use one Google Cloud project linked to Firebase. Configure its project ID as `FIREBASE_PROJECT_ID` for the FastAPI
service and use the same project when running Firebase CLI commands.

Authenticate the CLI tools and, separately, Application Default Credentials for local SDK use:

```bash
gcloud auth login
gcloud config set project PROJECT_ID
gcloud auth application-default login
gcloud auth application-default set-quota-project PROJECT_ID
firebase login
```

Replace `PROJECT_ID` and other uppercase placeholders with your own values. Cloud commands below select their project
explicitly. Personal `.firebaserc` aliases are ignored; use `--project PROJECT_ID` or create your own aliases with
`firebase use --add`. Do not commit them: the
[Firebase CLI guidance for starter projects](https://firebase.google.com/docs/cli#source_control_and_project_aliases)
recommends leaving this file out of source control. Local emulator recipes always use `demo-test` instead.

Enable only the products used by the deployment target:

- Authentication and Firestore in Native mode for the FastAPI profile API;
- Vertex AI for the `dad_joke` function;
- Cloud Storage for Firebase only if you plan to use the checked-in storage rules.

The repository uses `europe-west4` for Firestore and Functions. The Function's Vertex AI client uses the `global`
endpoint. Storage location is selected when the bucket is provisioned rather than in `firebase.json`. Choose the Cloud
Run service region explicitly when deploying the FastAPI container.

## APIs and IAM

Enable the relevant APIs for your deployment:

- `run.googleapis.com` for Cloud Run and the function's backing service;
- `cloudfunctions.googleapis.com` for Firebase CLI-managed function deployment;
- `firestore.googleapis.com` for Firestore;
- `aiplatform.googleapis.com` for the Genkit Vertex AI function;
- `artifactregistry.googleapis.com` for the FastAPI image and function build artifacts;
- `cloudbuild.googleapis.com` for manual FastAPI image builds and Firebase's function source build;
- `logging.googleapis.com` for build and runtime logs;
- `secretmanager.googleapis.com` only when injecting managed secrets.

Enable APIs in the Google Cloud console for the selected project, or use `gcloud services enable API_NAME --project
PROJECT_ID` for each required API. The identity enabling APIs needs `serviceusage.services.enable`.

Create a dedicated FastAPI runtime service account in **IAM & Admin > Service Accounts**. Record its email locally as
`RUNTIME_SERVICE_ACCOUNT` for the deployment command. For the Function, identify the runtime service account used by
your Firebase deployment and grant its permissions to that identity. Grant only the roles needed by each component:

- FastAPI: `roles/datastore.user`; Cloud Run captures the service's structured stdout without a Logging API client;
- `dad_joke` function: `roles/aiplatform.user`; Cloud Run captures the Function's structured stdout without a Logging
  API client;
- intended `dad_joke` callers: `roles/run.invoker` on the function's backing Cloud Run service;
- Secret Manager consumers: `roles/secretmanager.secretAccessor` for only the required secrets.

Deployment permissions are separate from runtime IAM. The FastAPI deployer needs permission to create/update the Cloud
Run service and act as its runtime identity; image building and publishing also require Cloud Build and Artifact
Registry permissions for the submitting identity and the project's build service account. Use the current
[Cloud Run deployment permissions](https://cloud.google.com/run/docs/deploying#required_roles) and
[Cloud Build service account guidance](https://cloud.google.com/build/docs/cloud-build-service-account) to configure
the actual identities in your project. Firebase deployers need the applicable
[Firebase deployment permissions](https://firebase.google.com/docs/projects/iam/roles-predefined-product#functions).
Runtime roles alone do not grant deployment access.

Do not grant project-wide `Editor`. Prefer the Cloud Run or Functions runtime service account and Application Default
Credentials. For local development, prefer `gcloud auth application-default login`; use a downloaded service-account
key only when necessary, keep it outside the repository, and point `GOOGLE_APPLICATION_CREDENTIALS` to it.

## Optional local MCP connections

Cloud MCP connections are not enabled by this repository. After configuring a project you control, you can create
either or both of the following ignored files. Merge the relevant entries into any personal configuration already
present rather than replacing unrelated servers.

For VS Code, create `.vscode/mcp.json`:

```json
{
  "servers": {
    "firebase": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "firebase-tools@latest", "mcp", "--only", "auth,firestore,functions,storage"]
    },
    "google_cloud_logging": {
      "type": "http",
      "url": "https://logging.googleapis.com/mcp",
      "headers": {
        "Authorization": "Bearer ${env:GOOGLE_CLOUD_ACCESS_TOKEN}",
        "x-goog-user-project": "${env:GOOGLE_CLOUD_PROJECT}"
      }
    }
  }
}
```

For Codex, create `.codex/config.toml`:

```toml
[mcp_servers.google_cloud_logging]
url = "https://logging.googleapis.com/mcp"
bearer_token_env_var = "GOOGLE_CLOUD_ACCESS_TOKEN"
env_http_headers = { "x-goog-user-project" = "GOOGLE_CLOUD_PROJECT" }
enabled_tools = ["list_log_entries", "list_log_names"]

[mcp_servers.firebase]
command = "npx"
args = ["-y", "firebase-tools@latest", "mcp", "--only", "auth,firestore,functions,storage"]
```

Firebase uses the credentials available to the Firebase CLI and your explicitly selected project. Its `--only`
option selects feature groups, not emulator-only access; core tools remain available. See the
[Firebase MCP documentation](https://firebase.google.com/docs/ai-assistance/mcp-server). Cloud Logging uses
`GOOGLE_CLOUD_ACCESS_TOKEN` for OAuth and `GOOGLE_CLOUD_PROJECT` as the `x-goog-user-project` quota project; neither
value belongs in tracked configuration. Grant the Cloud Logging identity permission to use MCP tools
(`roles/mcp.toolUser`) and the Logging permissions required by the enabled tools and log views. Use the
[Cloud Logging MCP setup guide](https://docs.cloud.google.com/logging/docs/use-logging-mcp) and
[Logging access control](https://cloud.google.com/logging/docs/access-control) to choose roles for the intended access.
The Codex example exposes only `list_log_entries` and `list_log_names`; this client tool filter does not replace IAM.

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

`GOOGLE_CLOUD_ACCESS_TOKEN` contains one access-token value; it is not a self-refreshing credential. Run
`source ~/.zshrc` to generate a fresh value, then restart VS Code or Codex from that refreshed environment so the MCP
client inherits it. If Cloud Logging MCP returns `Auth required`, repeat both steps. Refreshing only the shell does not
change the value held by an already-running client, while restarting a client from an environment that still contains
the expired value does not fix authentication. Never commit the expanded token, and use this convenience setup only on
a trusted workstation because child processes inherit it. If setting the ADC quota project fails, the local identity
needs `serviceusage.services.use`, commonly granted through `roles/serviceusage.serviceUsageConsumer`. See
[Google Cloud MCP authentication](https://docs.cloud.google.com/mcp/authenticate-mcp) for authentication options and
token-refresh limitations.

Restart clients after adding or removing workspace MCP configuration. A running client can retain a connection until
restart. User-global MCP settings and CLI credentials are independent; removing a workspace file does not revoke them.

## FastAPI configuration

These settings are defined in `app/core/config.py`:

| Variable | Required in deployment | Default | Purpose |
|---|---:|---|---|
| `FIREBASE_PROJECT_ID` | Profile API | none | Firebase and Firestore project ID; checked when a protected route needs Firebase |
| `FIRESTORE_DATABASE` | No | `(default)` | Optional named Firestore database |
| `GOOGLE_APPLICATION_CREDENTIALS` | Local only | unset | Explicit credential-file path; omit on Cloud Run |
| `ENVIRONMENT` | No | `production` | `development`, `test`, or `production` |
| `LOG_LEVEL` | No | `INFO` | Application log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |
| `CORS_ORIGINS` | Browser clients only | empty | JSON array or comma-separated explicit origins; wildcard is rejected |

`PORT` is consumed by the development and container commands, not by `Settings`; it defaults to `8080`.

Example Cloud Run values:

```dotenv
FIREBASE_PROJECT_ID=your-project-id
ENVIRONMENT=production
LOG_LEVEL=INFO
FIRESTORE_DATABASE=(default)
CORS_ORIGINS=["https://app.example.com"]
```

## Local development and tests

Install and run the FastAPI app from the repository root:

```bash
cp .env.example .env
just install
just serve
```

The API documentation is available at `http://127.0.0.1:8080/api-docs`; `/health` is a dependency-free liveness
endpoint and does not verify Firebase, Firestore, GitHub, or Vertex AI readiness. Public routes and `/openapi.json`
start without initializing Firebase. Configure `FIREBASE_PROJECT_ID` and ADC before exercising a profile operation.

The application-level inbound request limit is fixed by the portable API contract at 1,000,000 bytes for POST and
PATCH. It is intentionally not environment-configurable. Configure Cloud Run and any gateway so they do not reject a
smaller body before the application can return its portable 413 response.

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
for generated URLs and HSTS decisions; do not remove those runtime flags without verifying `/health`, generated
pagination links, and security headers through the deployed service.

The Dockerfile produces a standalone, locally runnable image containing the operating system and Python runtime. It is
not a scratch-based application image, so do not combine it with Cloud Run `--base-image` or `--automatic-updates`.

### Manual Cloud Run deployment

After completing project, API, and IAM setup, create a Docker-format Artifact Registry repository in your chosen region
if it does not already exist:

```bash
gcloud artifacts repositories create REPO \
  --project PROJECT_ID \
  --location REGION \
  --repository-format docker
```

Build from the repository root, publish the image, and deploy it with the dedicated runtime identity:

```bash
GIT_SHA="$(git rev-parse HEAD)"
gcloud builds submit --project PROJECT_ID \
  --tag "REGION-docker.pkg.dev/PROJECT_ID/REPO/fastapi-playground:${GIT_SHA}"

gcloud run deploy fastapi-playground \
  --project PROJECT_ID \
  --image "REGION-docker.pkg.dev/PROJECT_ID/REPO/fastapi-playground:${GIT_SHA}" \
  --platform managed \
  --region REGION \
  --service-account RUNTIME_SERVICE_ACCOUNT \
  --set-env-vars FIREBASE_PROJECT_ID=PROJECT_ID,ENVIRONMENT=production,LOG_LEVEL=INFO \
  --allow-unauthenticated
```

`RUNTIME_SERVICE_ACCOUNT` is the email of the service account you created, not your user account. The public Cloud Run
invocation policy allows the health and public API routes; profile routes still verify Firebase ID tokens. Keep the
model-backed Function private. If organization policy prohibits public invocation, use an approved gateway or private
deployment and supply Cloud Run authentication separately from the profile API's Firebase authentication.

Add `FIRESTORE_DATABASE` and explicit `CORS_ORIGINS` when needed. Cloud Run supplies ADC through the runtime identity;
do not mount a downloaded key or set `GOOGLE_APPLICATION_CREDENTIALS` there. Retrieve your service URL from the console
or `gcloud run services describe fastapi-playground --project PROJECT_ID --region REGION --format='value(status.url)'`.
Verify `/health`, `/openapi.json`, HTTPS security headers, and profile operations with a synthetic principal. No GitHub
App connection or automatic repository trigger is needed for this manual flow. See
[Artifact Registry creation](https://cloud.google.com/sdk/gcloud/reference/artifacts/repositories/create),
[manual builds](https://cloud.google.com/sdk/gcloud/reference/builds/submit), and
[Cloud Run deployment](https://cloud.google.com/run/docs/deploying).

## Deploy the Firebase function

The `dad_joke` HTTP function uses:

- runtime `python314` in `europe-west4`;
- 512 MiB memory, concurrency `1`, and `TIMEOUT_SEC` default `120`;
- `MIN_INSTANCES` default `0` and `MAX_INSTANCES` default `2`;
- Genkit with the `global` Vertex AI endpoint and auto-updating `gemini-pro-latest` alias configured in
  `functions/main.py`;
- structured Genkit JSON logging captured by Cloud Run functions;
- private IAM invocation; unauthenticated internet requests cannot consume model quota.

The alias tracks Google's current Gemini Pro model, avoiding a hard dependency on a dated model ID. It can also change
model behavior, latency, and cost without a repository deployment. Keep structured output validation and Function tests
in place, monitor production behavior and spend, and verify alias availability and quota before deployment. See the
[Genkit Python model documentation](https://genkit.dev/docs/python/models/) and
[Python Vertex AI plugin documentation](https://genkit.dev/docs/python/integrations/vertex-ai/).

Firebase deployment uses the intentionally lean `functions/requirements.txt`, which pins only the direct runtime
packages to versions from `functions/uv.lock`; the deployment installer resolves their transitive dependencies. Run
`just update` to refresh both lockfiles and regenerate the lean file, or `just sync-functions-requirements` after changing
direct Functions dependencies. The restricted `uv export` command uses `--only-emit-package` for every direct package;
`just check-functions-requirements` rejects drift and accidental unrestricted exports.

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
  --project PROJECT_ID \
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
project separately formats Genkit logs as structured JSON for platform capture; it does not configure a Genkit trace or
metric exporter.

Both observability middleware components use W3C Trace Context Level 1. The service intentionally omits v2's
privacy-sensitive raw path, direct peer address, User-Agent, and exception-message access fields; route templates and
operation IDs remain available as low-cardinality dimensions.

The portable route boundary converts malformed or wrong-scope pagination cursors to controlled 400 responses before a
service call. When verifying this path in your own deployment, use Cloud Logging or an explicitly configured Cloud
Logging MCP connection to correlate the request ID with its single 400 access record and confirm that no adjacent
`Exception in ASGI application` ERROR was emitted for the same request window.

The GitHub family is a credential-free public projection. The outbound client is fixed to `https://api.github.com`,
the REST version `2026-03-10`, four allowlisted request fields, identity encoding, a ten-second whole-operation
deadline, three validated same-origin redirects, and a 4 MiB response bound. Do not configure `GITHUB_TOKEN` for these
routes: route wiring intentionally ignores ambient and inbound credentials. Anonymous quota exhaustion is a controlled
429 and may make live smoke checks nondeterministic; deterministic tests use a local transport double.

Production checklist:

- keep `ENVIRONMENT=production` so production-only error redaction and HSTS remain enabled;
- use `LOG_LEVEL=INFO` unless a temporary, explicitly reviewed verbosity change is needed;
- terminate TLS at Cloud Run and verify HSTS on HTTPS responses;
- keep the model-backed function private and grant `roles/run.invoker` only to intended callers;
- configure explicit `CORS_ORIGINS` for browser clients;
- keep Cloud Run and gateway body limits at or above the portable 1,000,000-byte application limit;
- inject production secrets from Secret Manager rather than plain values;
- rebuild the custom image regularly for OS, Python, and dependency patches;
- configure log-based alerts and budgets for Vertex AI usage.

## Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| Profile request returns 503 | Firebase or Firestore dependency is unavailable | Project ID, ADC, database name, network, and `roles/datastore.user` |
| Auth returns 401 | Missing, expired, revoked, disabled-user, or invalid token | Bearer token and `WWW-Authenticate` response header |
| Auth returns 503 | Firebase verification dependency unavailable | ADC, network access, public-key retrieval, and `Retry-After` |
| GitHub request returns 429 | Anonymous GitHub quota exhausted | `Retry-After` and optional `X-RateLimit-Reset`; do not add a token as a workaround |
| GitHub request returns 502/504 | Upstream contract, transport, size, redirect, or deadline failure | Correlated safe access log; provider diagnostics stay out of public responses |
| Function returns 400 | Unsupported `topic` query value | Use `work`, `tech`, `food`, or `relationships` |
| Function returns 401/403 before handler | Missing identity token or caller IAM | ID token and `roles/run.invoker` on the backing service |
| Function returns 503 | Genkit or Vertex AI failure | Vertex API, global endpoint/model alias availability, ADC, IAM, and quotas |
| E2E test skips | Firestore emulator is not running on `127.0.0.1:7030` | Run `just emulators` |
| CORS is blocked | Origin is absent from `CORS_ORIGINS` | Configure an exact allowed origin |

## One-time profile data migration

Existing documents written by the retired contract use `email`, `marketing`, and `terms`. The accepted representation
uses `contact_email`, `marketing_opt_in`, and `terms_accepted` in Firestore while the public API uses camelCase. The
same migration hardens document keys for principals that are not one safe Firestore document-ID segment, without
changing the public principal ID. Deployment of this revision over existing data therefore requires the checked-in
migration:

```bash
# Read-only validation; requires explicit target configuration and ADC.
uv run python -m scripts.migrate_profiles

# Writes only after every current document validates. Run only with operational approval.
uv run python -m scripts.migrate_profiles --apply
```

Quiesce all profile traffic, back up Firestore, verify the target project and database, run the dry run, apply, then
rerun the dry run until it reports `pending=0`. The script compares each document again inside its write transaction
and requires canonical-key documents to contain already-canonical values rather than approving in-memory
normalization. Key moves create an absent target and delete the source in the same transaction. It is safe to rerun. An
interrupted collection-wide run can be partial, so keep the retired revision away from migrated records and do not
start the new revision until the final dry run is clean. If an earlier deployment admitted a custom Firebase UID
containing `/`, inventory those principals from the backup before cutover because the retired raw path may have
addressed a nested document that a top-level collection scan cannot find. Deploy and verify the new revision with a
dedicated synthetic principal before restoring profile traffic. Partial adoption becomes unsafe with the first
migrated document; rollback requires restoring the backup together with the retired revision. The migration is not
part of `just check`, deployment automation, or application startup.
