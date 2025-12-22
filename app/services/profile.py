"""
Profile service with async Firestore operations.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from google.cloud import firestore

from app.core.firebase import get_async_firestore_client
from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from app.middleware import log_audit_event
from app.models.profile import PROFILE_COLLECTION, Profile, ProfileCreate, ProfileUpdate

if TYPE_CHECKING:
    from google.cloud.firestore import AsyncClient, AsyncDocumentReference, AsyncTransaction


class ProfileService:
    """
    Service for profile CRUD operations using async Firestore.
    """

    def __init__(self) -> None:
        self.collection_name = PROFILE_COLLECTION

    def _get_client(self) -> AsyncClient:
        return get_async_firestore_client()

    @staticmethod
    @firestore.async_transactional
    async def _create_in_transaction(  # pragma: no cover
        transaction: AsyncTransaction,
        doc_ref: AsyncDocumentReference,
        data: dict,
    ) -> None:
        # Tested via E2E tests with Firebase emulators; unit tests mock this method
        snapshot = await doc_ref.get(transaction=transaction)
        if snapshot.exists:
            raise ProfileAlreadyExistsError("Profile already exists")
        transaction.set(doc_ref, data)

    async def create_profile(self, user_id: str, profile_data: ProfileCreate) -> Profile:
        """
        Create a new profile for the given user.
        """
        client = self._get_client()
        doc_ref = client.collection(self.collection_name).document(user_id)

        now = datetime.now(UTC)
        profile_dict = {
            "id": user_id,
            **profile_data.model_dump(),
            "created_at": now,
            "updated_at": now,
        }

        transaction = client.transaction()
        await self._create_in_transaction(transaction, doc_ref, profile_dict)

        log_audit_event("create", user_id, "profile", user_id, "success")

        return Profile(**profile_dict)

    async def get_profile(self, user_id: str) -> Profile:
        """
        Get profile by user ID.

        Raises:
            ProfileNotFoundError: If profile does not exist.
        """
        client = self._get_client()
        doc_ref = client.collection(self.collection_name).document(user_id)
        snapshot = await doc_ref.get()

        if not snapshot.exists:
            raise ProfileNotFoundError("Profile not found")

        data = snapshot.to_dict()
        if not data:
            raise ProfileNotFoundError("Profile not found")

        return Profile(**data)

    @staticmethod
    @firestore.async_transactional
    async def _update_in_transaction(  # pragma: no cover
        transaction: AsyncTransaction,
        doc_ref: AsyncDocumentReference,
        updates: dict,
    ) -> bool:
        # Tested via E2E tests with Firebase emulators; unit tests mock this method
        snapshot = await doc_ref.get(transaction=transaction)
        if not snapshot.exists:
            return False
        transaction.update(doc_ref, updates)
        return True

    async def update_profile(self, user_id: str, profile_data: ProfileUpdate) -> Profile:
        """
        Update an existing profile.

        Raises:
            ProfileNotFoundError: If profile does not exist.
        """
        client = self._get_client()
        doc_ref = client.collection(self.collection_name).document(user_id)

        update_dict = {k: v for k, v in profile_data.model_dump(exclude_unset=True).items() if v is not None}

        if not update_dict:
            return await self.get_profile(user_id)

        update_dict["updated_at"] = datetime.now(UTC)

        transaction = client.transaction()
        exists = await self._update_in_transaction(transaction, doc_ref, update_dict)

        if not exists:
            raise ProfileNotFoundError("Profile not found")

        log_audit_event("update", user_id, "profile", user_id, "success")

        return await self.get_profile(user_id)

    @staticmethod
    @firestore.async_transactional
    async def _delete_in_transaction(  # pragma: no cover
        transaction: AsyncTransaction,
        doc_ref: AsyncDocumentReference,
    ) -> dict | None:
        # Tested via E2E tests with Firebase emulators; unit tests mock this method
        snapshot = await doc_ref.get(transaction=transaction)
        if not snapshot.exists:
            return None
        data = snapshot.to_dict()
        transaction.delete(doc_ref)
        return data

    async def delete_profile(self, user_id: str) -> Profile:
        """
        Delete a profile by user ID.

        Raises:
            ProfileNotFoundError: If profile does not exist.
        """
        client = self._get_client()
        doc_ref = client.collection(self.collection_name).document(user_id)

        transaction = client.transaction()
        deleted_data = await self._delete_in_transaction(transaction, doc_ref)

        if deleted_data is None:
            raise ProfileNotFoundError("Profile not found")

        log_audit_event("delete", user_id, "profile", user_id, "success")

        return Profile(**deleted_data)
