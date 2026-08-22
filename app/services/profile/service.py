"""Atomic async Firestore profile lifecycle service."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from google.api_core import exceptions as google_exceptions
from google.cloud import firestore

from app.core.firebase import get_async_firestore_client
from app.exceptions.profile import (
    ProfileAlreadyExistsError,
    ProfileDependencyError,
    ProfileNotFoundError,
    ProfileTimestampOverflowError,
)
from app.models.profile import PROFILE_COLLECTION, Profile, ProfileCreate, ProfileUpdate
from app.models.types import truncate_clock_milliseconds
from app.services.profile.document_id import firestore_profile_document_id

if TYPE_CHECKING:
    from google.cloud.firestore import AsyncClient, AsyncDocumentReference, AsyncTransaction

logger = logging.getLogger(__name__)
_MAX_TIMESTAMP = datetime(9999, 12, 31, 23, 59, 59, 999000, tzinfo=UTC)
_CANONICAL_PROFILE_KEYS = {
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


def _log_profile_audit_event(action: str) -> None:
    """Emit a mutation audit without a principal identifier or profile data."""
    logger.info(
        "Profile mutation committed",
        extra={"audit": {"action": action, "resource_type": "profile", "result": "success"}},
    )


def _profile_from_storage(data: dict[str, Any], *, expected_id: str) -> Profile:
    """Validate the canonical persisted representation at the service boundary."""
    if set(data) != _CANONICAL_PROFILE_KEYS or data.get("id") != expected_id:
        raise ValueError("profile document shape is invalid")
    profile = Profile.model_validate(
        {
            "id": data.get("id"),
            "firstName": data.get("first_name"),
            "lastName": data.get("last_name"),
            "contactEmail": data.get("contact_email"),
            "phoneNumber": data.get("phone_number"),
            "marketingOptIn": data.get("marketing_opt_in"),
            "termsAccepted": data.get("terms_accepted"),
            "createdAt": data.get("created_at"),
            "updatedAt": data.get("updated_at"),
        },
        strict=True,
    )
    if profile.model_dump(by_alias=False) != data:
        raise ValueError("profile document shape is invalid")
    return profile


def _profile_to_storage(profile: Profile) -> dict[str, Any]:
    return profile.model_dump(by_alias=False)


class ProfileService:
    """Principal-keyed profile CRUD using native conditional and transactional writes."""

    def __init__(
        self,
        *,
        client: AsyncClient | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.collection_name = PROFILE_COLLECTION
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))

    def _get_client(self) -> AsyncClient:
        if self._client is not None:
            return self._client
        try:
            return get_async_firestore_client()
        except Exception as error:
            raise ProfileDependencyError from error

    async def create_profile(self, user_id: str, profile_data: ProfileCreate) -> Profile:
        """Conditionally create the complete profile in one native write."""
        document_id = firestore_profile_document_id(user_id)
        client = self._get_client()
        document = client.collection(self.collection_name).document(document_id)
        now = truncate_clock_milliseconds(self._clock())
        profile = Profile.model_validate(
            {
                "id": user_id,
                "firstName": profile_data.first_name,
                "lastName": profile_data.last_name,
                "contactEmail": profile_data.contact_email,
                "phoneNumber": profile_data.phone_number,
                "marketingOptIn": profile_data.marketing_opt_in,
                "termsAccepted": profile_data.terms_accepted,
                "createdAt": now,
                "updatedAt": now,
            },
            strict=True,
        )
        try:
            await document.create(_profile_to_storage(profile))
        except google_exceptions.Conflict as error:
            raise ProfileAlreadyExistsError from error
        except (google_exceptions.GoogleAPICallError, google_exceptions.RetryError, TimeoutError) as error:
            raise ProfileDependencyError from error
        _log_profile_audit_event("create")
        return profile

    async def get_profile(self, user_id: str) -> Profile:
        """Read the current principal profile without writing."""
        document_id = firestore_profile_document_id(user_id)
        document = self._get_client().collection(self.collection_name).document(document_id)
        try:
            snapshot = await document.get()
        except (google_exceptions.GoogleAPICallError, google_exceptions.RetryError, TimeoutError) as error:
            raise ProfileDependencyError from error
        if not snapshot.exists:
            raise ProfileNotFoundError
        data = snapshot.to_dict()
        if data is None:
            raise ValueError("profile document shape is invalid")
        return _profile_from_storage(data, expected_id=user_id)

    @staticmethod
    @firestore.async_transactional
    async def _update_in_transaction(
        transaction: AsyncTransaction,
        document: AsyncDocumentReference,
        user_id: str,
        updates: dict[str, Any],
        now: datetime,
    ) -> tuple[Profile | None, bool]:
        snapshot = await document.get(transaction=transaction)
        if not snapshot.exists:
            return None, False
        stored = snapshot.to_dict()
        if stored is None:
            raise ValueError("profile document shape is invalid")
        current = _profile_from_storage(stored, expected_id=user_id)
        changed = any(getattr(current, name) != value for name, value in updates.items())
        if not changed:
            return current, False
        if current.updated_at == _MAX_TIMESTAMP:
            raise ProfileTimestampOverflowError
        next_updated_at = max(now, current.updated_at + timedelta(milliseconds=1))
        stored_updates = {**updates, "updated_at": next_updated_at}
        candidate = _profile_from_storage({**stored, **stored_updates}, expected_id=user_id)
        transaction.update(document, stored_updates)
        return candidate, True

    async def update_profile(self, user_id: str, profile_data: ProfileUpdate) -> Profile:
        """Atomically apply one validated non-empty patch or perform no write."""
        updates = profile_data.model_dump(exclude_unset=True, by_alias=False)
        now = truncate_clock_milliseconds(self._clock())
        document_id = firestore_profile_document_id(user_id)
        client = self._get_client()
        document = client.collection(self.collection_name).document(document_id)
        try:
            profile, changed = await self._update_in_transaction(client.transaction(), document, user_id, updates, now)
        except ProfileTimestampOverflowError:
            raise
        except (google_exceptions.GoogleAPICallError, google_exceptions.RetryError, TimeoutError) as error:
            raise ProfileDependencyError from error
        if profile is None:
            raise ProfileNotFoundError
        if changed:
            _log_profile_audit_event("update")
        return profile

    @staticmethod
    @firestore.async_transactional
    async def _delete_in_transaction(
        transaction: AsyncTransaction,
        document: AsyncDocumentReference,
    ) -> bool:
        snapshot = await document.get(transaction=transaction)
        if not snapshot.exists:
            return False
        transaction.delete(document)
        return True

    async def delete_profile(self, user_id: str) -> None:
        """Atomically distinguish one successful deletion from absence."""
        document_id = firestore_profile_document_id(user_id)
        client = self._get_client()
        document = client.collection(self.collection_name).document(document_id)
        try:
            deleted = await self._delete_in_transaction(client.transaction(), document)
        except (google_exceptions.GoogleAPICallError, google_exceptions.RetryError, TimeoutError) as error:
            raise ProfileDependencyError from error
        if not deleted:
            raise ProfileNotFoundError
        _log_profile_audit_event("delete")
