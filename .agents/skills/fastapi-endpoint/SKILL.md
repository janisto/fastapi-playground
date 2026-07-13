---
name: fastapi-endpoint
description: Create or change fastapi-playground FastAPI endpoints, including routing, typed dependencies, authentication, JSON or CBOR, Problem Details, schema links, OpenAPI metadata, and tests.
---

# FastAPI endpoints

Read `AGENTS.md`, the neighboring router, `app/api/__init__.py`, relevant models and services, and existing integration
tests before editing an endpoint.

## Architecture

- Put transport behavior in `app/api/`, domain behavior in `app/services/`, and shared infrastructure in `app/core/`.
- Register business routers on `v1_router`; keep health and schema discovery unversioned.
- Use `CBORRoute` for business endpoints so request and response negotiation stays consistent.
- Use typed dependency aliases from `app/dependencies.py`; protected routes must use `CurrentUser`.
- Return Pydantic response models directly. Do not introduce response envelopes or raw dictionaries.

## Public contract

For every operation, define a stable `<resource>_<action>` operation ID, summary, description, reachable success and
error responses, and a precise return type. Use 201 plus `Location` for persistent creation and 204 without a model for
deletion. Keep paths without trailing slashes because redirects are disabled.

Add a `Link: </schemas/Model.json>; rel="describedBy"` header and an absolute runtime `$schema` URL to modeled
responses. Keep router-level Problem Details declarations and route-specific statuses aligned with runtime behavior.
Use the `openapi-contract` skill as well when a route, model, error, authentication rule, or response header changes the
public contract.

Let Pydantic and FastAPI validate request data. Use `Literal` for fixed query values and constrained annotated aliases
for shared validation. Re-raise expected domain exceptions; log and replace unexpected failures with generic 500
details. Never log request bodies, credentials, or profile PII.

## Implementation sequence

1. Update separate request and response models.
2. Add or change the service contract and domain exceptions.
3. Implement the thin route and register a new router when needed.
4. Inspect the generated OpenAPI operation and component schemas.
5. Add integration tests for success, validation, authentication or authorization, domain failures, headers, and
   representative JSON and CBOR behavior.

Run the focused tests, then `just lint`, `just typing`, and `just test`.
