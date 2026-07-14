---
name: openapi-contract
description: Maintain and verify fastapi-playground generated OpenAPI 3.1, FastAPI operation metadata, Pydantic component schemas, RFC 9457 errors, bearer security, schema discovery, and API documentation when routes, models, errors, or public API behavior change.
---

# OpenAPI contract maintenance

Read `AGENTS.md`, `app/main.py`, `app/api/schemas.py`, and the affected routers, models, exception handling, and contract
tests before changing the public API. When media types or `Accept` behavior changes, also read
`app/core/content_negotiation.py` and `app/core/cbor.py`.

## Architecture

Treat the public contract as four connected surfaces:

1. FastAPI decorators, return annotations, dependencies, and Pydantic models define operations and component schemas.
2. `fastapi_app.openapi()` produces the OpenAPI 3.1 document served at `/openapi.json` and rendered at `/api-docs` and
   `/api-redoc`.
3. `populate_schema_cache()` derives `/schemas/{Model}.json` documents from OpenAPI components after router
   registration.
4. Runtime behavior adds RFC 9457 JSON or CBOR errors, authentication, request limits, and response headers that the
   generated contract must describe accurately where FastAPI supports them.

Do not add a hand-maintained specification or generated artifact. The small schema-component registration in
`app/core/openapi.py` is the source for error schemas that are documented inline and served through `/schemas/`.

## Contract rules

- Keep every operation ID stable and unique, paths free of trailing slashes, and summaries and descriptions accurate.
- Document every reachable success and error status with the correct schema and implemented JSON or CBOR media types;
  omit content for 204 responses.
- Keep request and response models separate. Reject unknown request fields and preserve examples, constraints, and UTC
  millisecond serialization in component schemas.
- Follow the `AGENTS.md` naming policy in component properties and request parameters: use `snake_case` directly and do
  not introduce camelCase aliases. Preserve externally standardized names exactly.
- Mark protected operations through the existing bearer dependency and verify the generated security requirement.
- Document `Location` and `Link` headers when runtime behavior emits them.
- Keep Problem Details models aligned with strict RFC 9457 responses, validation error details, production redaction,
  and `WWW-Authenticate` or `Retry-After` headers where applicable.
- Keep runtime JSON and CBOR negotiation tests aligned with the documented request, success, and error contract. Do not
  claim a media type in OpenAPI merely because a custom route can serialize it.
- Keep `$schema` on standalone schema documents only. Response instances use stable relative `describedBy` links, and
  every advertised schema must resolve through `/schemas/`.

## Workflow

1. Inspect route registration, runtime behavior, dependencies, request and response models, and exception mapping.
2. Update operation metadata, models, field names, or shared error declarations at their source.
3. Add focused runtime tests for changed statuses, validation, authentication, negotiation, and headers.
4. Inspect `/openapi.json` and the affected `/schemas/{Model}.json` documents through the composed application.
5. Assert cross-cutting invariants when appropriate: exact path and method sets, unique operation IDs, protected-route
   security, reachable status codes, snake_case component properties, component references, and schema-link resolution.
6. Reject unrelated schema churn and contract claims that differ from observable runtime behavior.

Run focused integration tests, then `just lint`, `just typing`, and `just test`.

## Review checklist

- OpenAPI remains 3.1 and contains every public operation exactly once.
- Operation IDs are unique and protected routes declare bearer authentication.
- Request, success, validation, and Problem Details schemas match runtime bodies.
- 201 responses document `Location`; 204 responses have no body; paginated responses document `Link`.
- Standalone schema documents declare the JSON Schema dialect, and `describedBy` links resolve to the intended schema.
- `/openapi.json`, `/api-docs`, `/api-redoc`, and hidden `/schemas/` routes retain their intended visibility.
