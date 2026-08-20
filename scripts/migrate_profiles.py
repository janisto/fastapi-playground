"""
One-time old-profile to portable-profile Firestore migration.

The command is dry-run by default. ``--apply`` performs one transaction per
document after every candidate has passed validation; run only with explicit
authority against the intended project and database.
"""

import argparse
import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from google.cloud import firestore

from app.core.firebase import close_async_firestore_client, get_async_firestore_client, initialize_firebase
from app.models.profile import PROFILE_COLLECTION, Profile
from app.models.types import truncate_clock_milliseconds

if TYPE_CHECKING:
    from google.cloud.firestore import AsyncDocumentReference, AsyncTransaction

_OLD_KEYS = {
    "id",
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "marketing",
    "terms",
    "created_at",
    "updated_at",
}
_CANONICAL_KEYS = {
    "id",
    "first_name",
    "last_name",
    "contact_email",
    "phone_number",
    "marketing_opt_in",
    "terms_accepted",
    "created_at",
    "updated_at",
}


def _canonical_document(data: dict[str, object]) -> dict[str, object]:
    if set(data) != _OLD_KEYS:
        raise ValueError("profile is not in the exact retired representation")
    created_at = data["created_at"]
    updated_at = data["updated_at"]
    if not isinstance(created_at, datetime) or not isinstance(updated_at, datetime):
        raise TypeError("profile timestamps are invalid")
    profile = Profile.model_validate(
        {
            "id": data["id"],
            "firstName": data["first_name"],
            "lastName": data["last_name"],
            "contactEmail": data["email"],
            "phoneNumber": data["phone_number"],
            "marketingOptIn": data["marketing"],
            "termsAccepted": data["terms"],
            "createdAt": truncate_clock_milliseconds(created_at),
            "updatedAt": truncate_clock_milliseconds(updated_at),
        },
        strict=True,
    )
    return profile.model_dump(by_alias=False)


def _validate_canonical_document(data: dict[str, object]) -> None:
    if set(data) != _CANONICAL_KEYS:
        raise ValueError("profile is neither the retired nor canonical representation")
    profile = Profile.model_validate(
        {
            "id": data["id"],
            "firstName": data["first_name"],
            "lastName": data["last_name"],
            "contactEmail": data["contact_email"],
            "phoneNumber": data["phone_number"],
            "marketingOptIn": data["marketing_opt_in"],
            "termsAccepted": data["terms_accepted"],
            "createdAt": data["created_at"],
            "updatedAt": data["updated_at"],
        },
        strict=True,
    )
    if profile.model_dump(by_alias=False) != data:
        raise ValueError("canonical profile values are invalid")


@firestore.async_transactional
async def _replace_document(
    transaction: AsyncTransaction,
    document: AsyncDocumentReference,
    expected: dict[str, object],
    replacement: dict[str, object],
) -> None:
    snapshot = await document.get(transaction=transaction)
    if not snapshot.exists or snapshot.to_dict() != expected:
        raise RuntimeError("profile changed during migration")
    transaction.set(document, replacement)


async def migrate(*, apply: bool) -> tuple[int, int, int]:
    """Validate all documents, then optionally replace each with a compare-before-write transaction."""
    initialize_firebase()
    client = get_async_firestore_client()
    candidates: list[tuple[AsyncDocumentReference, dict[str, object], dict[str, object]]] = []
    validated = 0
    async for snapshot in client.collection(PROFILE_COLLECTION).stream():
        data = snapshot.to_dict()
        if not data:
            raise ValueError("empty profile document")
        if data.get("id") != snapshot.reference.id:
            raise ValueError("profile identity does not match its document ID")
        validated += 1
        if set(data) == _CANONICAL_KEYS:
            _validate_canonical_document(data)
            continue
        candidates.append((snapshot.reference, data, _canonical_document(data)))
    if apply:
        for document, expected, replacement in candidates:
            await _replace_document(client.transaction(), document, expected, replacement)
    return validated, len(candidates), len(candidates) if apply else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate retired profile field names to the accepted portable model")
    parser.add_argument("--apply", action="store_true", help="perform writes after all documents validate")
    arguments = parser.parse_args()
    try:
        validated, pending, written = asyncio.run(migrate(apply=arguments.apply))
    finally:
        close_async_firestore_client()
    print(f"validated={validated} pending={pending} written={written}")  # noqa: T201 - CLI result


if __name__ == "__main__":
    main()
