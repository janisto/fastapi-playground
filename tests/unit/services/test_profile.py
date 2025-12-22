"""
Unit tests for ProfileService.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from pytest_mock import MockerFixture

from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from app.models.profile import ProfileCreate, ProfileUpdate
from app.services.profile import ProfileService
from tests.mocks.firestore import FakeAsyncClient


def _make_profile_data(
    user_id: str = "user-123",
    firstname: str = "John",
    lastname: str = "Doe",
    email: str = "john@example.com",
    phone_number: str = "+358401234567",
    marketing: bool = True,
    terms: bool = True,
) -> dict[str, Any]:
    """
    Create profile data dict for tests.
    """
    now = datetime.now(UTC)
    return {
        "id": user_id,
        "firstname": firstname,
        "lastname": lastname,
        "email": email,
        "phone_number": phone_number,
        "marketing": marketing,
        "terms": terms,
        "created_at": now,
        "updated_at": now,
    }


def _make_profile_create(
    firstname: str = "John",
    lastname: str = "Doe",
    email: str = "john@example.com",
    phone_number: str = "+358401234567",
    marketing: bool = True,
    terms: bool = True,
) -> ProfileCreate:
    """
    Create ProfileCreate model for tests.
    """
    return ProfileCreate(
        firstname=firstname,
        lastname=lastname,
        email=email,
        phone_number=phone_number,
        marketing=marketing,
        terms=terms,
    )


def _make_profile_update(
    firstname: str | None = None,
    lastname: str | None = None,
    email: str | None = None,
    phone_number: str | None = None,
    marketing: bool | None = None,
    terms: bool | None = None,
) -> ProfileUpdate:
    """
    Create ProfileUpdate model for tests.
    """
    return ProfileUpdate(
        firstname=firstname,
        lastname=lastname,
        email=email,
        phone_number=phone_number,
        marketing=marketing,
        terms=terms,
    )


@pytest.fixture
def fake_db(mocker: MockerFixture) -> FakeAsyncClient:
    """
    Patch Firestore client with fake.
    """
    db = FakeAsyncClient()
    mocker.patch("app.services.profile.get_async_firestore_client", return_value=db)
    return db


@pytest.fixture(autouse=True)
def mock_transactional_methods(mocker: MockerFixture, fake_db: FakeAsyncClient) -> None:
    """
    Mock the transactional methods in ProfileService.

    The @firestore.async_transactional decorator is applied at import time,
    so we need to patch the decorated methods directly to use our fake
    transaction logic.
    """
    from app.exceptions import ProfileAlreadyExistsError
    from app.services.profile import ProfileService as PS

    async def fake_create_in_transaction(
        transaction: object,
        doc_ref: object,
        data: dict[str, Any],
    ) -> None:
        doc_id = getattr(doc_ref, "id", None)
        if doc_id and doc_id in fake_db._store:
            raise ProfileAlreadyExistsError("Profile already exists")
        if doc_id:
            fake_db._store[doc_id] = data

    async def fake_update_in_transaction(
        transaction: object,
        doc_ref: object,
        updates: dict[str, Any],
    ) -> bool:
        doc_id = getattr(doc_ref, "id", None)
        if not doc_id or doc_id not in fake_db._store:
            return False
        fake_db._store[doc_id].update(updates)
        return True

    async def fake_delete_in_transaction(
        transaction: object,
        doc_ref: object,
    ) -> dict[str, Any] | None:
        doc_id = getattr(doc_ref, "id", None)
        if not doc_id or doc_id not in fake_db._store:
            return None
        data = fake_db._store.pop(doc_id)
        return data

    mocker.patch.object(PS, "_create_in_transaction", staticmethod(fake_create_in_transaction))
    mocker.patch.object(PS, "_update_in_transaction", staticmethod(fake_update_in_transaction))
    mocker.patch.object(PS, "_delete_in_transaction", staticmethod(fake_delete_in_transaction))


@pytest.fixture(autouse=True)
def mock_audit_log(mocker: MockerFixture) -> None:
    """
    Mock audit logging to avoid side effects.
    """
    mocker.patch("app.services.profile.log_audit_event")


class TestProfileServiceGetProfile:
    """
    Tests for ProfileService.get_profile().
    """

    async def test_returns_profile_when_exists(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify get_profile returns Profile when document exists.
        """
        fake_db._store["user-123"] = _make_profile_data(user_id="user-123")

        service = ProfileService()
        profile = await service.get_profile("user-123")

        assert profile.id == "user-123"
        assert profile.firstname == "John"
        assert profile.lastname == "Doe"
        assert profile.email == "john@example.com"

    async def test_returns_profile_with_all_fields(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify all profile fields are returned correctly.
        """
        fake_db._store["user-456"] = _make_profile_data(
            user_id="user-456",
            firstname="Jane",
            lastname="Smith",
            email="jane@example.com",
            phone_number="+358409876543",
            marketing=False,
            terms=True,
        )

        service = ProfileService()
        profile = await service.get_profile("user-456")

        assert profile.id == "user-456"
        assert profile.firstname == "Jane"
        assert profile.lastname == "Smith"
        assert profile.email == "jane@example.com"
        assert profile.phone_number == "+358409876543"
        assert profile.marketing is False
        assert profile.terms is True

    async def test_raises_not_found_when_missing(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify get_profile raises ProfileNotFoundError when document missing.
        """
        service = ProfileService()

        with pytest.raises(ProfileNotFoundError) as exc_info:
            await service.get_profile("nonexistent")

        assert "not found" in str(exc_info.value.detail).lower()

    async def test_raises_not_found_when_data_is_none(self, fake_db: FakeAsyncClient, mocker: MockerFixture) -> None:
        """
        Verify get_profile raises ProfileNotFoundError when to_dict returns None.

        This tests the edge case where the document exists but to_dict() returns None.
        We patch FakeDocumentSnapshot.to_dict to return None while keeping exists=True.
        """
        from tests.mocks.firestore import FakeDocumentSnapshot

        fake_db._store["user-123"] = _make_profile_data()

        original_to_dict = FakeDocumentSnapshot.to_dict

        def patched_to_dict(self: FakeDocumentSnapshot) -> dict[str, Any] | None:
            if self.id == "user-123":
                return None
            return original_to_dict(self)

        mocker.patch.object(FakeDocumentSnapshot, "to_dict", patched_to_dict)

        service = ProfileService()

        with pytest.raises(ProfileNotFoundError):
            await service.get_profile("user-123")


class TestProfileServiceCreateProfile:
    """
    Tests for ProfileService.create_profile().
    """

    async def test_creates_profile_successfully(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify create_profile stores data and returns Profile.
        """
        profile_create = _make_profile_create()

        service = ProfileService()
        profile = await service.create_profile("new-user", profile_create)

        assert profile.id == "new-user"
        assert profile.firstname == "John"
        assert profile.email == "john@example.com"
        assert "new-user" in fake_db._store

    async def test_sets_timestamps(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify create_profile sets created_at and updated_at.
        """
        profile_create = _make_profile_create()

        service = ProfileService()
        profile = await service.create_profile("user-ts", profile_create)

        assert profile.created_at is not None
        assert profile.updated_at is not None
        assert profile.created_at == profile.updated_at

    async def test_raises_already_exists_when_duplicate(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify create_profile raises ProfileAlreadyExistsError for duplicates.
        """
        fake_db._store["existing-user"] = _make_profile_data(user_id="existing-user")
        profile_create = _make_profile_create()

        service = ProfileService()

        with pytest.raises(ProfileAlreadyExistsError) as exc_info:
            await service.create_profile("existing-user", profile_create)

        assert "already exists" in str(exc_info.value.detail).lower()

    async def test_stores_all_fields(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify create_profile stores all input fields.
        """
        profile_create = _make_profile_create(
            firstname="Alice",
            lastname="Wonder",
            email="alice@example.com",
            phone_number="+358401111111",
            marketing=False,
            terms=True,
        )

        service = ProfileService()
        await service.create_profile("alice-id", profile_create)

        stored = fake_db._store["alice-id"]
        assert stored["firstname"] == "Alice"
        assert stored["lastname"] == "Wonder"
        assert stored["email"] == "alice@example.com"
        assert stored["phone_number"] == "+358401111111"
        assert stored["marketing"] is False
        assert stored["terms"] is True


class TestProfileServiceUpdateProfile:
    """
    Tests for ProfileService.update_profile().
    """

    async def test_updates_single_field(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify update_profile updates a single field.
        """
        fake_db._store["user-123"] = _make_profile_data(user_id="user-123")
        profile_update = _make_profile_update(firstname="Updated")

        service = ProfileService()
        profile = await service.update_profile("user-123", profile_update)

        assert profile.firstname == "Updated"
        assert fake_db._store["user-123"]["firstname"] == "Updated"

    async def test_updates_multiple_fields(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify update_profile updates multiple fields at once.
        """
        fake_db._store["user-123"] = _make_profile_data(user_id="user-123")
        profile_update = _make_profile_update(
            firstname="New First",
            lastname="New Last",
            marketing=False,
        )

        service = ProfileService()
        profile = await service.update_profile("user-123", profile_update)

        assert profile.firstname == "New First"
        assert profile.lastname == "New Last"
        assert profile.marketing is False

    async def test_updates_updated_at_timestamp(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify update_profile updates the updated_at timestamp.
        """
        original_time = datetime(2024, 1, 1, tzinfo=UTC)
        fake_db._store["user-123"] = {
            **_make_profile_data(user_id="user-123"),
            "created_at": original_time,
            "updated_at": original_time,
        }
        profile_update = _make_profile_update(firstname="Updated")

        service = ProfileService()
        profile = await service.update_profile("user-123", profile_update)

        assert profile.updated_at > original_time

    async def test_raises_not_found_when_missing(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify update_profile raises ProfileNotFoundError when profile missing.
        """
        profile_update = _make_profile_update(firstname="Updated")

        service = ProfileService()

        with pytest.raises(ProfileNotFoundError) as exc_info:
            await service.update_profile("nonexistent", profile_update)

        assert "not found" in str(exc_info.value.detail).lower()

    async def test_returns_unchanged_profile_when_no_updates(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify update_profile returns unchanged profile when no fields provided.
        """
        original_data = _make_profile_data(user_id="user-123")
        fake_db._store["user-123"] = original_data
        profile_update = _make_profile_update()

        service = ProfileService()
        profile = await service.update_profile("user-123", profile_update)

        assert profile.firstname == original_data["firstname"]


class TestProfileServiceDeleteProfile:
    """
    Tests for ProfileService.delete_profile().
    """

    async def test_deletes_profile_successfully(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify delete_profile removes document from store.
        """
        fake_db._store["user-123"] = _make_profile_data(user_id="user-123")

        service = ProfileService()
        await service.delete_profile("user-123")

        assert "user-123" not in fake_db._store

    async def test_returns_deleted_profile(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify delete_profile returns the deleted Profile.
        """
        fake_db._store["user-123"] = _make_profile_data(
            user_id="user-123",
            firstname="ToDelete",
        )

        service = ProfileService()
        profile = await service.delete_profile("user-123")

        assert profile.id == "user-123"
        assert profile.firstname == "ToDelete"

    async def test_raises_not_found_when_missing(self, fake_db: FakeAsyncClient) -> None:
        """
        Verify delete_profile raises ProfileNotFoundError when profile missing.
        """
        service = ProfileService()

        with pytest.raises(ProfileNotFoundError) as exc_info:
            await service.delete_profile("nonexistent")

        assert "not found" in str(exc_info.value.detail).lower()


class TestProfileServiceInit:
    """
    Tests for ProfileService initialization.
    """

    def test_sets_collection_name(self) -> None:
        """
        Verify ProfileService sets correct collection name.
        """
        service = ProfileService()

        assert service.collection_name == "profiles"
