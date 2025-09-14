# Copilot Instructions

These guidelines define how AI agents and contributors should work in this FastAPI/Python repository. Use GitHub Issues/PRs for tracking, GitHub Actions for CI (if configured), and local tooling via uv and just.

---

## Workflow Principles

- Correctness first → Prioritize correctness, then readability/maintainability, then performance.
- Reflect before acting → After tool results, briefly summarize insights, list next options, and pick the best one.
- Parallelize independent steps → Run unrelated reads/checks in parallel to maximize efficiency.
- No leftovers → Remove temporary files/scripts/debug outputs before finishing. Keep `git status` clean aside from intended changes.
- Ask when unsure → If requirements are ambiguous, seek clarification rather than guessing.
- Well-supported dependencies → Prefer widely used, well-documented libraries with active maintenance.
- Security first → Never exfiltrate secrets; avoid network calls unless explicitly required. Do not log PII or secrets.

---

## Tech & Tooling

- Language/runtime: Python 3.13+
- Frameworks/libs: FastAPI, Pydantic v2, Uvicorn, Firebase Admin SDK, Google Cloud (Firestore/Logging/Secret Manager)
- Package/devenv: uv (+ virtualenv in `.venv`), Justfile for tasks
- Lint/format: Ruff (line-length 120; rules include ANN, FAST)
- Type checking: ty
- Testing: pytest, pytest-asyncio, coverage

Use uv consistently (do not mix with pip/poetry within this repo). Prefer `just` shortcuts where available.

---

## Coding Guidelines

- FastAPI style
  - Use `async def` for I/O-bound endpoints and services.
  - Validate inputs/outputs with Pydantic models; set `response_model` and explicit status codes.
  - Raise `HTTPException` with clear messages; add contextual logging on failures.
  - Keep routers thin; put business logic in `services/` and shared logic in `core/`.

- Types & structure
  - Add type hints everywhere. Avoid `Any`; prefer `typing.Protocol`, `TypedDict`, `Literal`, or `Annotated` as appropriate.
  - Reuse existing domain models; don’t duplicate types. Prefer narrow types over `dict[str, object]`.
  - Keep imports explicit; group as stdlib / third-party / local with blank lines.

- Configuration & secrets
  - Use `pydantic-settings` for config. Never hardcode secrets. Load via env or Secret Manager.
  - Do not log secrets or PII. Redact sensitive fields in logs.

- Error handling & logging
  - Use `app/core/logging.py` configuration. Include request context where useful.
  - Wrap critical paths in try/except with actionable messages; avoid silencing exceptions.

- Firebase/Google Cloud
  - Initialize Firebase/clients via `app/core/firebase.py` and dependencies. Inject via FastAPI dependencies.
  - Avoid direct network access in unit tests; use mocks/stubs.

- Style & linting
  - Follow Ruff; do not disable globally. Keep lines ≤120 chars. Prefer targeted `noqa` only when justified.
  - Keep code simple and idiomatic. Avoid premature abstractions.

---

## Testing Guidelines

1) Coverage & scope
   - Write tests for all new features and bug fixes.
   - Aim for 90%+ overall coverage, and 100% on critical business logic paths.
   - Include edge cases, error handling, and auth/permission scenarios.

2) Structure & style
   - Place tests under `tests/`, mirroring module names where practical.
   - Use `pytest` with `pytest-asyncio` for async tests (`@pytest.mark.asyncio`).
   - Unit tests must not use real network/Firestore; mock Firebase Admin/clients.
   - E2E/integration tests can use the FastAPI app test client; keep external calls mocked unless explicitly testing integrations.

3) Running
   - `just test` for all tests; `just cov` for coverage report; see CLI section below.

---

## API Documentation

- FastAPI generates OpenAPI automatically. Keep `response_model`, `responses`, `tags`, and docstrings accurate.
- Provide request/response examples where useful using FastAPI `examples` in model/route definitions.
- If introducing a shared error format, define a canonical error model (e.g., `ErrorResponse`) and reuse it across endpoints.

---

## Project Structure

- `app/` — FastAPI app: routers, models, services, core config, auth
- `tests/` — unit/integration/e2e tests
- `functions/` — Firebase Cloud Functions (Python 3.13) codebase (`main.py`, its own `requirements.txt`)
- `Justfile` — dev/test/build tasks
- `pyproject.toml` — dependencies and tool configs (Ruff, ty, pytest, coverage)

Keep routers focused on I/O and validation; put domain logic in `services/`; keep shared configuration/utilities in `core/`.

### Monorepo Considerations (FastAPI app + Cloud Functions)

When adding features, decide if logic belongs in the FastAPI service (`app/`) or a Cloud Function (`functions/`):

| Scenario | Prefer FastAPI (`app/`) | Prefer Cloud Function (`functions/`) |
| -------- | ----------------------- | ------------------------------------ |
| Multiple cohesive REST endpoints | ✅ | ❌ |
| Single lightweight webhook / experimental endpoint | ❌ | ✅ |
| Requires custom middleware chain / shared service layer | ✅ | ❌ |
| Spiky, low average traffic (cost optimize) | ⚠️ | ✅ |
| Long-lived streaming / websockets | ✅ | ❌ |

Cloud Functions specifics:
- Runtime pinned via `firebase.json` (`python313`, region `europe-west4`).
- Global scaling options in `functions/main.py` (memory 128MB; env-param `MIN_INSTANCES` default 0, `MAX_INSTANCES` default 2).
- Dependencies isolated in `functions/requirements.txt`; DO NOT automatically mirror all `pyproject.toml` deps—keep lean to reduce cold starts.
- Add new functions by decorating callables with `@https_fn.on_request()` (or other trigger types) inside `functions/main.py` (or split into modules imported by `main.py`).
- Deployment: `firebase deploy --only functions` (ensure you installed `functions/requirements.txt`).
- Emulator: `firebase emulators:start --only functions` (ports defined in `firebase.json`).
- Vertex / Generative AI support is optional—uncomment and configure client if needed.

Agent guidance:
1. If a change affects shared domain logic used by both environments, refactor into a neutral module under a new `shared/` or reuse `app/services/` only if no Firebase-only dependencies leak in.
2. Avoid importing FastAPI-specific middleware or app objects inside `functions/` code.
3. When editing both layers, create separate commits/patch hunks logically grouped (e.g., "feat(functions): add X" and "feat(api): expose X endpoint").
4. Keep environment variables documented in the top-level README when introducing new cross-environment config.
5. For tests of logic used in functions, write pure unit tests under `tests/unit/` that import the shared module—not the Firebase runtime wrapper—to avoid emulator coupling.

CI note: Currently CI focuses on the FastAPI app; if functions gain complex logic, add a lightweight import test (e.g., ensure `functions/main.py` loads) and possibly a dry-run deployment script.

---

## Useful CLI Commands (via just)

| Command           | Purpose                                               |
| ----------------- | ----------------------------------------------------- |
| `just serve`      | Run dev server on http://127.0.0.1:8080               |
| `just test`       | Run tests                                             |
| `just cov`        | Run tests with coverage (html report to `htmlcov/`)   |
| `just lint`       | Ruff check + format                                   |
| `just typing`     | Type checking via ty                                  |
| `just check-all`  | Run lint, test, and typing                        |
| `just modernize`  | Apply safe modernization via Ruff's pyupgrade rules   |
| `just install`    | Sync dependencies with uv                             |
| `just update`     | Upgrade dependencies with uv                          |
| `just clean`      | Remove caches and temporary files                     |
| `just fresh`      | Clean and reinstall                                   |

Notes
- You can override dev server port via `PORT` env (default 8080).
- For ad-hoc HTTP against the dev server: `just req <path> [args...]`.

---

## Pull Requests & Code Review

- PRs must include a clear description, rationale, and link to any related issue.
- Include/update tests and API docs where relevant.
- Use Conventional Commits for messages.
- Keep diffs focused; avoid unrelated refactors in the same PR.

Checklist for PRs
- [ ] Tests added/updated and passing locally (`just check-all`)
- [ ] Coverage meets target (aim ≥90%)
- [ ] Lint/type checks clean (Ruff/ty)
- [ ] API responses/docs accurate (response models, codes, examples)

---

## Secrets & Environment Variables

- Never commit secrets. Use a local `.env` (gitignored) and Secret Manager in production.
- Access config through settings classes (pydantic-settings); don’t read env directly in business logic.
- Don’t log secrets or PII; ensure logs redact sensitive fields.
- Typical env vars
  - `ENVIRONMENT`, `DEBUG`
  - `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON)
  - `FIREBASE_PROJECT_ID` (also used for trace correlation; `GCP_PROJECT_ID` deprecated)

---

## CI Required Checks (recommended)

Per change, run and require the following for green status:
- Lint/format: `just lint`
- Typecheck: `just typing`
- Tests: `just test` (or `just cov`) with coverage thresholds enforced
- Optional: container build and a basic smoke test (if Dockerized deployment is in use)

---

## Agent Execution Guardrails

- Reflect on tool results and pick the best next action before proceeding.
- Prefer batching independent read-only steps in parallel; avoid redundant reads.
- Clean up temporary files/scripts before finishing a task.
- Do not invent paths/APIs/commands—verify from repo or tooling.
- For runnable code changes, run minimal tests to validate, report PASS/FAIL succinctly, and iterate up to three targeted fixes if needed.
