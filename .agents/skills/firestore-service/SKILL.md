---
name: firestore-service
description: Create or change fastapi-playground async Firestore services, including ownership boundaries, transactions, timestamps, domain errors, audit records, emulator coverage, and dependency injection.
---

# Firestore services

Read `AGENTS.md`, `app/core/firebase.py`, the neighboring service and models, and existing unit and emulator tests before
editing persistence behavior.

## Service boundary

- Keep Firestore access under `app/services/<domain>/`; routers should depend on a narrow service through
  `app/dependencies.py`.
- Reuse `get_async_firestore_client()` and the collection constant exported by the domain models.
- Use the authenticated UID as the ownership boundary for user-owned data. Do not accept a client-selected owner ID.
- Keep stored field names and internal Pydantic model fields explicitly `snake_case`, with a deliberate one-way mapping
  to the public camelCase contract. Do not add compatibility reads or storage aliases for retired names.
- Never add test flags, production fakes, or network calls to unit tests.

## Transactions and data semantics

Use the native conditional `document.create()` for create-if-absent and `firestore.async_transactional` for
read-modify-write and delete-if-present operations. Create the transaction wrapper per operation; its mutable retry
state must not be shared across concurrent calls. Map SDK retry exhaustion chained from `Aborted` to a dependency
failure while preserving unrelated `ValueError` failures. Read the document through the transaction before writing. Map
absent documents and conflicts to domain exceptions rather than returning sentinel values across the service boundary.

Use timezone-aware `datetime.now(UTC)` timestamps. Preserve `created_at`; update `updated_at` only for real mutations.
For PATCH input, use `model_dump(exclude_unset=True)` and apply the domain's explicit-null policy consistently. Avoid an
extra read when the transaction already returns the merged document.

After a successful mutation, emit one structured audit record with action, resource type, and result. Do not log the
principal or resource identifier, profile fields, tokens, request bodies, or exception strings containing backend data.

## Verification

- Unit-test service behavior with the existing Firestore fakes or mocked transaction helper.
- Cover create conflicts, missing reads, empty snapshots, partial and empty updates, missing deletes, timestamp
  behavior, and audit emission.
- Use Firebase emulator E2E tests for real transaction and SDK behavior; do not claim transaction coverage from mocks.

Run focused service tests, then `just lint`, `just typing`, and `just test`. Run `just test-e2e` when transaction or
Firestore integration semantics change and the emulators are available.

When changing persisted fields, update models, storage mapping, fixtures, emulator assertions, and current contract
documentation together. Do not retain compatibility reads, aliases, or migration tools for retired playground schemas.

The async Firestore client's `close()` method is synchronous in the supported SDK. Call the repository lifecycle
helper without `await`, and keep shutdown in the lifespan `finally` block so failed requests cannot skip cleanup.
