# Application test instructions

Scope: `tests/`. The root `AGENTS.md` also applies.
Repository paths are root-relative. Run commands from the repository root unless
another working directory is explicitly stated.

Use the local `adversarial-testing` and `pytest-testing` skills before changing
tests. Function tests follow [their own guide](../functions/AGENTS.md).

## Boundaries and assertions

- Use unit tests for pure functions, models, middleware, authentication branches,
  services, and Firestore fakes.
- Use integration tests for composed routing, middleware order, request IDs,
  negotiation, Problem Details, OpenAPI, and headers.
- Use E2E tests for real Firebase SDK and transaction semantics on local emulators.
  The emulator recipe uses synthetic `demo-test`; never target a deployed project.
- Assert exact status/media, relevant headers, decoded shape, service calls, error
  redaction, route metadata, and absence of sensitive output. Prefer parametrized
  input matrices and `AsyncMock` assertions for async calls.
- Unit and integration tests must not use real network or Firestore access.

## Commands

Run the narrowest useful target first:

```bash
just test-unit
just test-integration
just test
just cov
just emulators
just test-e2e
```

`just test-all` covers application, emulator, and independent Function tests.
Run E2E tests when Firestore transaction or SDK semantics change. The root guide
owns container validation requirements.
