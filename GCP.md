## Google Cloud & Firebase Setup

This guide provisions the infrastructure required for the FastAPI service (deployable to Cloud Run) and the optional Firebase Cloud Functions code under `functions/`. Steps are ordered; you can skip sections not relevant to your deployment model.

See:
- https://cloud.google.com/build/docs/automating-builds/github/connect-repo-github?generation=2nd-gen
- https://cloud.google.com/build/docs/automating-builds/github/build-repos-from-github?generation=2nd-gen

---
### 1. Create Projects
1. (If new) Create a Google Cloud Project (GCP). Note the `PROJECT_ID`.
2. Create / Link a Firebase project to the same GCP project (Firebase console). The Firebase project ID must match the `FIREBASE_PROJECT_ID` environment variable used by the app.

---
### 2. Enable Firebase Products (Console → Build)
Enable (region: `europe-west4` to match repo defaults):
- Firestore (Native mode) – location: `europe-west4`
- Cloud Storage for Firebase – location: `europe-west4`
- Authentication → Sign-in methods:
    - Phone (add test numbers if needed)
    - Google (configure OAuth consent & SHA if using Android, etc.)

Add a Web App in Firebase console (used by front-end clients only; not required for backend).

---
### 3. Service Account & Credentials
The backend prefers Application Default Credentials on Cloud Run / Functions. Locally you can:
1. Create a Service Account (e.g. `firebase-admin-sdk` or reuse the auto-created Admin SDK account).
2. Grant roles (see IAM section below).
3. Download a JSON key ONLY for local development; store outside version control. Point to it via:
     `GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/service_account.json`

Avoid deploying JSON keys to Cloud Run (use Workload Identity / default service account instead).

---
### 4. Required / Recommended GCP APIs
Enable the following in the GCP console or via `gcloud services enable`:
- `run.googleapis.com` (Cloud Run) – if deploying container
- `secretmanager.googleapis.com` – if you plan to store secrets (code currently just has a flag placeholder)
- `cloudbuild.googleapis.com` – if using Cloud Build triggers
- `containeranalysis.googleapis.com` – for image vulnerability scanning (optional but recommended)
- `binaryauthorization.googleapis.com` – optional (policy-based deploy control)
- `firestore.googleapis.com` (should auto-enable with Firestore)
- `storage.googleapis.com` (auto-enabled with Firebase Storage)

Vertex AI is not presently used in code; only enable if you intend to uncomment & use Vertex / Generative AI clients.

---
### 5. IAM Roles (Principle of Least Privilege)
Assign to the runtime service account (Cloud Run or Functions default). Consolidate where possible using predefined roles:

Minimum for current features:
- `roles/datastore.user` (Firestore access)
- `roles/logging.logWriter` (structured log export – though default often has it)

If using Secret Manager flag in future:
- `roles/secretmanager.secretAccessor`

Optional (only if needed):
- `roles/aiplatform.user` (Vertex AI; not active yet)

Do NOT broadly grant `Editor` in production.

---
### 6. Environment Variables (Match `app/core/config.py`)
These are consumed by the FastAPI app. Provide via Cloud Run console, `gcloud run deploy --set-env-vars`, or Cloud Build substitutions.

| Variable | Required | Description |
|----------|----------|-------------|
| `FIREBASE_PROJECT_ID` | Yes | Firebase / GCP project ID (trace correlation & Firestore) |
| `FIREBASE_PROJECT_NUMBER` | No | Project number (useful for some integrations) |
| `GOOGLE_APPLICATION_CREDENTIALS` | No (local) | Path to service account JSON locally. Omit in Cloud Run. |
| `ENVIRONMENT` | No | Environment label (`development`, `staging`, `production`) |
| `DEBUG` | No | Set `false` in production |
| `APP_ENVIRONMENT` | No | Optional metadata surfaced in logs |
| `APP_URL` | No | Public base URL (informational) |
| `SECRET_MANAGER_ENABLED` | No | Currently a placeholder flag (`true`/`false`) |
| `MAX_REQUEST_SIZE_BYTES` | No | Request size guard (default 1_000_000) |
| `CORS_ORIGINS` | No | Comma-separated origins (empty blocks all) |

Example (staging):
```
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PROJECT_NUMBER=1234567890
ENVIRONMENT=staging
DEBUG=false
APP_ENVIRONMENT=staging
APP_URL=https://your-service-europe-west4.run.app
SECRET_MANAGER_ENABLED=true
```

---
### 7. Local Development
1. Clone repo & install deps: `just install`
2. Create `.env` with at least `FIREBASE_PROJECT_ID` (and credentials path if needed).
3. Run: `just serve` → `http://127.0.0.1:8080/api-docs`
4. (Optional) Start Firebase emulators for Firestore/Auth/Functions:
     ```bash
     firebase emulators:start
     ```
5. Run tests: `just test` or `just cov`.

Firestore + Auth calls in tests are mocked; real GCP resources not required.

---
### 8. Container Build & Cloud Run Deployment
Build image locally (BuildKit is required for the `--mount` syntax used in the Dockerfile):
```bash
DOCKER_BUILDKIT=1 docker build -t gcr.io/PROJECT_ID/fastapi-playground:latest .
docker push gcr.io/PROJECT_ID/fastapi-playground:latest
```

> **Note:** Docker 23.0+ uses BuildKit by default. If using an older Docker version, prefix the build command with `DOCKER_BUILDKIT=1`.
Deploy:
```bash
gcloud run deploy fastapi-playground \
    --image gcr.io/PROJECT_ID/fastapi-playground:latest \
    --region europe-west4 \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars FIREBASE_PROJECT_ID=PROJECT_ID,ENVIRONMENT=production,DEBUG=false
```
Add additional env vars with a comma list or `--set-secrets` (if migrating to Secret Manager later).

Automatic base image updates (optional; see Dockerfile comments) via `--base-image` & `--automatic-updates` flags.

Health check: Cloud Run uses `/` for default checks by default; you can configure a custom probe path `/health` (returns `{ "status": "healthy" }`).

---
### 9. Cloud Build (2nd Gen) – Optional CI/CD
If you want automated builds from GitHub:
1. Connect repository (Cloud Build Console → Repositories → Connect).
2. Create a build trigger:
     - Source: GitHub, branch pattern (e.g. `main`)
     - Build config: Use the included `cloudbuild.yaml`
     - Service account: one with Cloud Run Deploy + Artifact Registry Write + (optional) Secret Manager Access
3. Configure substitutions if needed (see `cloudbuild.yaml` for available options).

**Important: BuildKit Requirement**

The Dockerfile uses BuildKit features (`RUN --mount=type=cache,...`) for efficient caching. The default `gcr.io/cloud-builders/docker` image does **NOT** support BuildKit natively.

The included `cloudbuild.yaml` uses the official Docker image with BuildKit enabled. If you create your own build config, ensure you:
- Use the official `docker` image (not `gcr.io/cloud-builders/docker`)
- Set `DOCKER_BUILDKIT=1` environment variable

**Why the official `docker` image?**
- The `gcr.io/cloud-builders/docker` image uses an older Docker version that doesn't support BuildKit's `--mount` option
- The official `docker` image (from Docker Hub) includes Docker 23.x+ with full BuildKit support
- Setting `DOCKER_BUILDKIT=1` enables BuildKit for advanced Dockerfile features

4. (Optional) Add a build-time health check script that curls `/health` after deploying to verify rollout.

Secrets: Use Secret Manager with Cloud Build by adding `--set-secrets VAR=projects/<num>/secrets/<name>:latest` if you introduce secrets later.

---
### 10. Firebase Cloud Functions (Python) (Optional Alternate / Complement)
Contained in `functions/` with regional + scaling config:
- Runtime: `python314`
- Region: `europe-west4`
- Scaling: `MIN_INSTANCES` / `MAX_INSTANCES` env params (default 0/2)

Deploy:
```bash
cd functions && uv sync
firebase deploy --only functions
```

Emulate locally:
```bash
firebase emulators:start --only functions
```

Use Functions when you need a small single endpoint (webhook, prototype) and keep the full FastAPI service for cohesive REST APIs & middleware features.

---
### 11. Logging & Trace Correlation
The FastAPI app emits structured JSON logs (see `app/core/logging.py`). When Cloud Run forwards requests with `X-Cloud-Trace-Context`, logs embed:
- `trace`: `projects/<FIREBASE_PROJECT_ID>/traces/<TRACE_ID>`
- `spanId`: Provided span

No direct Cloud Logging API usage (stdout ingestion). Ensure log-based metrics / alerts are configured in GCP as needed.

---
### 12. Security Notes & Hardening Checklist
- Remove unused deps (`python-jose`, `httpx`) if not planned.
- Enforce HTTPS (Cloud Run provides TLS terminator; HSTS enabled by middleware when configured).
- Set `DEBUG=false` in production.
- Restrict CORS explicitly (`CORS_ORIGINS`).
- Consider enabling Binary Authorization + vulnerability scanning for supply chain assurance.
- Migrate any future secrets to Secret Manager (currently only placeholder flag).

---
### 13. Troubleshooting
| Symptom | Cause | Fix |
|---------|-------|-----|
| Cloud Build: `the --mount option requires BuildKit` | Using `gcr.io/cloud-builders/docker` which doesn't support BuildKit | Use the included `cloudbuild.yaml` which uses the official `docker` image with `DOCKER_BUILDKIT=1` |
| 500 + log `Firestore client is not available` | Missing permissions or Firestore not initialized | Check IAM role `datastore.user` and region | 
| Auth 401/403 | Missing/invalid `Authorization` header | Provide valid Firebase ID token |
| Cold start latency | Min instances = 0 | Raise `MIN_INSTANCES` (Cloud Run: `--min-instances`) or Functions env param |
| CORS blocked | `CORS_ORIGINS` unset | Add origins env var |

---
### 14. Quick Reference Commands
```bash
# Local
just serve
just test

# Container build & push (BuildKit required)
DOCKER_BUILDKIT=1 docker build -t gcr.io/PROJECT_ID/fastapi-playground:latest .
docker push gcr.io/PROJECT_ID/fastapi-playground:latest

# Deploy Cloud Run
gcloud run deploy fastapi-playground --image gcr.io/PROJECT_ID/fastapi-playground:latest --region europe-west4 --allow-unauthenticated \
    --set-env-vars FIREBASE_PROJECT_ID=PROJECT_ID,ENVIRONMENT=production,DEBUG=false

# Cloud Build (uses cloudbuild.yaml with BuildKit)
gcloud builds submit --config=cloudbuild.yaml

# Functions deploy
cd functions && uv sync && firebase deploy --only functions
```
