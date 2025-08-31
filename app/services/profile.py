"""Profile service for Firestore operations."""

import logging
from datetime import UTC, datetime

from google.cloud import firestore

from app.core.config import get_settings
from app.core.firebase import get_firestore_client
from app.models.profile import Profile, ProfileCreate, ProfileUpdate

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for profile operations in Firestore."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.collection_name = self.settings.firestore_collection_profiles

    def _get_collection(self) -> firestore.CollectionReference:
        """Get the profiles collection reference."""
        db = get_firestore_client()
        return db.collection(self.collection_name)

    async def create_profile(self, user_id: str, profile_data: ProfileCreate) -> Profile:
        """
        Create a new profile for a user.

        Args:
            user_id: The Firebase user ID
            profile_data: The profile data to create

        Returns:
            Profile: The created profile

        Raises:
            ValueError: If profile already exists for user
        """
        try:
            collection = self._get_collection()

            # Check if profile already exists
            existing = await self.get_profile(user_id)
            if existing:
                raise ValueError(f"Profile already exists for user {user_id}")

            # Create profile document
            now = datetime.now(UTC)
            profile_dict = {
                "id": user_id,
                "firstname": profile_data.firstname,
                "lastname": profile_data.lastname,
                "email": profile_data.email,
                "phone_number": profile_data.phone_number,
                "marketing": profile_data.marketing,
                "terms": profile_data.terms,
                "created_at": now,
                "updated_at": now,
            }

            # Save to Firestore
            collection.document(user_id).set(profile_dict)

            logger.info(f"Created profile for user {user_id}")

            return Profile(**profile_dict)

        except Exception as e:
            logger.error(f"Error creating profile for user {user_id}: {e}")
            raise

    async def get_profile(self, user_id: str) -> Profile | None:
        """
        Get a profile by user ID.

        Args:
            user_id: The Firebase user ID

        Returns:
            Profile: The profile if found, None otherwise
        """
        try:
            collection = self._get_collection()
            doc = collection.document(user_id).get()

            if not doc.exists:
                return None

            data = doc.to_dict()
            if not data:
                return None

            return Profile(**data)

        except Exception as e:
            logger.error(f"Error getting profile for user {user_id}: {e}")
            raise

    async def update_profile(self, user_id: str, profile_data: ProfileUpdate) -> Profile | None:
        """
        Update an existing profile.

        Args:
            user_id: The Firebase user ID
            profile_data: The profile data to update

        Returns:
            Profile: The updated profile if found, None otherwise
        """
        try:
            collection = self._get_collection()
            doc_ref = collection.document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                return None

            # Build update dictionary with only non-None values
            update_dict = {}
            for field, value in profile_data.model_dump(exclude_unset=True).items():
                if value is not None:
                    update_dict[field] = value

            if not update_dict:
                # No updates to apply
                data = doc.to_dict()
                return Profile(**data) if data else None

            # Add updated timestamp
            update_dict["updated_at"] = datetime.now(UTC)

            # Update document
            doc_ref.update(update_dict)

            # Get updated document
            updated_doc = doc_ref.get()
            data = updated_doc.to_dict()

            logger.info(f"Updated profile for user {user_id}")

            return Profile(**data) if data else None

        except Exception as e:
            logger.error(f"Error updating profile for user {user_id}: {e}")
            raise

    async def delete_profile(self, user_id: str) -> bool:
        """
        Delete a profile by user ID.

        Args:
            user_id: The Firebase user ID

        Returns:
            bool: True if profile was deleted, False if not found
        """
        try:
            collection = self._get_collection()
            doc_ref = collection.document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                return False

            doc_ref.delete()

            logger.info(f"Deleted profile for user {user_id}")

            return True

        except Exception as e:
            logger.error(f"Error deleting profile for user {user_id}: {e}")
            raise


# Global service instance
profile_service = ProfileService()
