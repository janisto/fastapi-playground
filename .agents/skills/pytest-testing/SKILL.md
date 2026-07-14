---
name: pytest-testing
description: Write or review fastapi-playground tests using pytest, FastAPI TestClient, async tests, dependency overrides, Firestore fakes, Firebase emulators, HTTPX2, coverage, and repository fixtures.
---

# Pytest testing

Read `AGENTS.md`, the implementation under test, the relevant suite's `conftest.py`, and neighboring tests before
choosing a boundary. Fixtures are scoped under `tests/unit/`, `tests/integration/`, `tests/e2e/`, and `functions/tests/`.

## Choose the narrowest useful test

- Pure models, helpers, services, and isolated middleware belong in `tests/unit/`.
- Composed routing, handlers, middleware order, negotiation, and exception responses belong in `tests/integration/`.
- Real Auth or Firestore SDK behavior belongs in `tests/e2e/` with local Firebase emulators.
- Firebase Function handler and deployment-manifest behavior belongs in `functions/tests/`; isolate Genkit telemetry and
  reflection infrastructure in test configuration and never call Vertex AI.

Use the shared fixtures and helpers before adding new ones. Override FastAPI dependencies on `fastapi_app`, while HTTP
clients target the exported outer `app` so request IDs and response-wide middleware are exercised. Always clean up
overrides. Do not add production test hooks, environment backdoors, sleeps, or real network access to unit or
integration tests.

Assert observable contracts: exact status, relevant headers, decoded response shape, Problem Details, JSON and CBOR
negotiation, authentication and authorization, body limits, request IDs, stale cursors, and absence of sensitive log
fields. Prefer parametrization for validation matrices and `AsyncMock` assertions for async service calls.

For public models, assert representative complete JSON and CBOR property sets and generated schema properties in
`snake_case`; do not only assert a resource envelope or one unaffected field. For persisted models, assert Firestore
keys use the same names. These tests enforce the naming policy that static Python linting cannot see.

Use `pytest-mock` for call-aware patching, `monkeypatch` for environment isolation, HTTPX2 for HTTP requests, and
`pytest-httpx2` for outbound mocks. With automatic asyncio mode, do not add `pytest.mark.asyncio` to ordinary async
tests.

## Commands

Run the focused file or node first, then the relevant suite:

```bash
just test-unit
just test-integration
just test-functions
just test
just cov
just test-e2e
```

Finish code changes with `just lint`, `just typing`, `just typing-functions`, `just test`, and `just test-functions` for
repository-wide changes.
