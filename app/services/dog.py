"""Dog service for Firestore operations."""

import logging
from datetime import UTC, datetime

from app.core.firebase import get_firestore_client
from app.models.dog import DOG_COLLECTION, Dog, DogCreate, DogUpdate

logger = logging.getLogger(__name__)


class DogService:
    """Service for dog operations in Firestore."""

    def __init__(self) -> None:
        # Use centralized constant for collection name to avoid scattering magic strings / env coupling.
        self.collection_name = DOG_COLLECTION

    def _get_collection(self) -> object:
        """Get the dogs collection reference."""
        client = get_firestore_client()
        return client.collection(self.collection_name)

    async def create_dog(self, owner_uid: str, dog_data: DogCreate) -> Dog:
        """Create a new dog in Firestore.

        Args:
            owner_uid: Firebase user ID of the dog's owner
            dog_data: Dog data to create

        Returns:
            Dog: The created dog with metadata

        Raises:
            Exception: If creation fails
        """
        try:
            collection = self._get_collection()
            doc_ref = collection.document()
            dog_id = doc_ref.id

            now = datetime.now(UTC)

            dog_dict = {
                **dog_data.model_dump(),
                "id": dog_id,
                "owner_uid": owner_uid,
                "created_at": now,
                "updated_at": now,
            }

            doc_ref.set(dog_dict)

            logger.info("Dog created", extra={"dog_id": dog_id, "owner_uid": owner_uid})
            return Dog(**dog_dict)

        except Exception as e:
            logger.error(f"Error creating dog for user {owner_uid}: {e}", extra={"owner_uid": owner_uid})
            raise

    async def get_dog(self, dog_id: str) -> Dog | None:
        """Get a dog by ID.

        Args:
            dog_id: The dog's unique identifier

        Returns:
            Dog | None: The dog if found, None otherwise
        """
        try:
            collection = self._get_collection()
            doc_ref = collection.document(dog_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.debug("Dog not found", extra={"dog_id": dog_id})
                return None

            return Dog(**doc.to_dict())

        except Exception as e:
            logger.error(f"Error retrieving dog {dog_id}: {e}", extra={"dog_id": dog_id})
            raise

    async def get_dogs_by_owner(self, owner_uid: str) -> list[Dog]:
        """Get all dogs for a specific owner.

        Args:
            owner_uid: Firebase user ID of the owner

        Returns:
            list[Dog]: List of dogs owned by the user
        """
        try:
            collection = self._get_collection()
            docs = collection.where("owner_uid", "==", owner_uid).stream()

            dogs = [Dog(**doc.to_dict()) for doc in docs]

            logger.debug("Dogs retrieved for owner", extra={"owner_uid": owner_uid, "count": len(dogs)})
            return dogs

        except Exception as e:
            logger.error(f"Error retrieving dogs for user {owner_uid}: {e}", extra={"owner_uid": owner_uid})
            raise

    async def update_dog(self, dog_id: str, owner_uid: str, dog_data: DogUpdate) -> Dog | None:
        """Update an existing dog.

        Args:
            dog_id: The dog's unique identifier
            owner_uid: Firebase user ID (for ownership verification)
            dog_data: Dog data to update

        Returns:
            Dog | None: The updated dog if found and owned by user, None otherwise

        Raises:
            ValueError: If dog exists but is not owned by the user
            Exception: If update fails
        """
        try:
            collection = self._get_collection()
            doc_ref = collection.document(dog_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.debug("Dog not found for update", extra={"dog_id": dog_id})
                return None

            existing_dog = doc.to_dict()

            # Verify ownership
            if existing_dog.get("owner_uid") != owner_uid:
                logger.warning(
                    "Unauthorized dog update attempt",
                    extra={"dog_id": dog_id, "owner_uid": owner_uid, "actual_owner": existing_dog.get("owner_uid")},
                )
                raise ValueError("Not authorized to update this dog")

            # Build update dict with only provided fields
            update_data = dog_data.model_dump(exclude_unset=True)
            if not update_data:
                # No fields to update, return existing
                return Dog(**existing_dog)

            update_data["updated_at"] = datetime.now(UTC)
            doc_ref.update(update_data)

            # Get updated document
            updated_doc = doc_ref.get()
            logger.info("Dog updated", extra={"dog_id": dog_id, "owner_uid": owner_uid})
            return Dog(**updated_doc.to_dict())

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating dog {dog_id}: {e}", extra={"dog_id": dog_id, "owner_uid": owner_uid})
            raise

    async def delete_dog(self, dog_id: str, owner_uid: str) -> bool:
        """Delete a dog.

        Args:
            dog_id: The dog's unique identifier
            owner_uid: Firebase user ID (for ownership verification)

        Returns:
            bool: True if deleted, False if not found

        Raises:
            ValueError: If dog exists but is not owned by the user
            Exception: If deletion fails
        """
        try:
            collection = self._get_collection()
            doc_ref = collection.document(dog_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.debug("Dog not found for deletion", extra={"dog_id": dog_id})
                return False

            existing_dog = doc.to_dict()

            # Verify ownership
            if existing_dog.get("owner_uid") != owner_uid:
                logger.warning(
                    "Unauthorized dog deletion attempt",
                    extra={"dog_id": dog_id, "owner_uid": owner_uid, "actual_owner": existing_dog.get("owner_uid")},
                )
                raise ValueError("Not authorized to delete this dog")

            doc_ref.delete()
            logger.info("Dog deleted", extra={"dog_id": dog_id, "owner_uid": owner_uid})
            return True

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error deleting dog {dog_id}: {e}", extra={"dog_id": dog_id, "owner_uid": owner_uid})
            raise


# Singleton instance
dog_service = DogService()
