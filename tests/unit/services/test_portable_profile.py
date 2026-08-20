"""Atomic profile lifecycle tests at the service/persistence-double boundary."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
from google.api_core import exceptions as google_exceptions

from app.exceptions import (
    ProfileAlreadyExistsError,
    ProfileDependencyError,
    ProfileNotFoundError,
    ProfileTimestampOverflowError,
)
from app.models.profile import Profile, ProfileCreate, ProfileUpdate
from app.services.profile.service import ProfileService, _log_profile_audit_event

_UPDATE_BODY = cast("Any", ProfileService._update_in_transaction).to_wrap
_DELETE_BODY = cast("Any", ProfileService._delete_in_transaction).to_wrap


class Snapshot:
    def __init__(self, value: dict[str, Any] | None) -> None:
        self.exists = value is not None
        self._value = value

    def to_dict(self) -> dict[str, Any] | None:
        return None if self._value is None else dict(self._value)


class Document:
    def __init__(self, client: Client, identifier: str) -> None:
        self.client = client
        self.identifier = identifier

    async def create(self, value: dict[str, Any]) -> None:
        async with self.client.lock:
            if self.identifier in self.client.store:
                raise google_exceptions.Conflict("exists")
            self.client.store[self.identifier] = dict(value)
            self.client.write_count += 1

    async def get(self, *, transaction: object | None = None) -> Snapshot:
        del transaction
        return Snapshot(self.client.store.get(self.identifier))


class Collection:
    def __init__(self, client: Client) -> None:
        self.client = client

    def document(self, identifier: str) -> Document:
        return Document(self.client, identifier)


class Transaction:
    def __init__(self, client: Client) -> None:
        self.client = client

    def update(self, document: Document, updates: dict[str, Any]) -> None:
        self.client.store[document.identifier].update(updates)
        self.client.write_count += 1

    def delete(self, document: Document) -> None:
        self.client.store.pop(document.identifier)
        self.client.write_count += 1


class Client:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.write_count = 0

    def collection(self, name: str) -> Collection:
        assert name == "profiles"
        return Collection(self)

    def transaction(self) -> Transaction:
        return Transaction(self)


@pytest.fixture(autouse=True)
def atomic_transaction_double(monkeypatch: pytest.MonkeyPatch) -> None:
    async def update(
        transaction: Transaction,
        document: Document,
        user_id: str,
        updates: dict[str, Any],
        now: datetime,
    ) -> tuple[Profile | None, bool]:
        async with transaction.client.lock:
            return await _UPDATE_BODY(transaction, document, user_id, updates, now)

    async def delete(transaction: Transaction, document: Document) -> bool:
        async with transaction.client.lock:
            return await _DELETE_BODY(transaction, document)

    monkeypatch.setattr(ProfileService, "_update_in_transaction", staticmethod(update))
    monkeypatch.setattr(ProfileService, "_delete_in_transaction", staticmethod(delete))


def _create(first_name: str = "Ada") -> ProfileCreate:
    return ProfileCreate.model_validate(
        {
            "firstName": first_name,
            "lastName": "Lovelace",
            "contactEmail": "Ada@EXAMPLE.COM",
            "phoneNumber": "+358401234567",
            "marketingOptIn": False,
            "termsAccepted": True,
        },
        strict=True,
    )


async def test_create_is_conditional_complete_and_millisecond_normalized() -> None:
    client = Client()

    def clock() -> datetime:
        return datetime(2026, 7, 30, 12, 0, 0, 123999, tzinfo=UTC)

    service = ProfileService(client=cast("Any", client), clock=clock)
    profile = await service.create_profile("principal-123", _create())
    assert profile.created_at == datetime(2026, 7, 30, 12, 0, 0, 123000, tzinfo=UTC)
    assert profile.updated_at == profile.created_at
    assert set(client.store["principal-123"]) == {
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
    original = dict(client.store["principal-123"])
    with pytest.raises(ProfileAlreadyExistsError):
        await service.create_profile("principal-123", _create("Grace"))
    assert client.store["principal-123"] == original
    assert client.write_count == 1


async def test_two_synchronized_creates_have_one_winner_and_one_conflict() -> None:
    client = Client()
    service = ProfileService(
        client=cast("Any", client),
        clock=lambda: datetime(2026, 7, 30, tzinfo=UTC),
    )
    outcomes = await asyncio.gather(
        service.create_profile("principal", _create("Ada")),
        service.create_profile("principal", _create("Grace")),
        return_exceptions=True,
    )
    assert sum(not isinstance(outcome, Exception) for outcome in outcomes) == 1
    assert sum(isinstance(outcome, ProfileAlreadyExistsError) for outcome in outcomes) == 1
    assert client.write_count == 1
    assert client.store["principal"]["first_name"] in {"Ada", "Grace"}


async def test_noop_patch_commits_no_write_and_real_patch_advances_monotonically() -> None:
    client = Client()
    service = ProfileService(
        client=cast("Any", client),
        clock=lambda: datetime(2020, 1, 1, tzinfo=UTC),
    )
    await service.create_profile("principal", _create())
    original = await service.get_profile("principal")
    writes = client.write_count
    noop = ProfileUpdate.model_validate({"firstName": "Ada"}, strict=True)
    unchanged = await service.update_profile("principal", noop)
    assert unchanged == original
    assert client.write_count == writes

    changed = await service.update_profile(
        "principal",
        ProfileUpdate.model_validate({"marketingOptIn": True}, strict=True),
    )
    assert changed.created_at == original.created_at
    assert changed.updated_at == original.updated_at.replace(microsecond=1000)
    assert changed.marketing_opt_in is True
    assert client.write_count == writes + 1


async def test_maximum_timestamp_real_patch_fails_before_write() -> None:
    client = Client()
    maximum = datetime(9999, 12, 31, 23, 59, 59, 999000, tzinfo=UTC)
    service = ProfileService(client=cast("Any", client), clock=lambda: maximum)
    client.store["principal"] = {
        "id": "principal",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "contact_email": "Ada@example.com",
        "phone_number": "+358401234567",
        "marketing_opt_in": False,
        "terms_accepted": True,
        "created_at": maximum,
        "updated_at": maximum,
    }
    with pytest.raises(ProfileTimestampOverflowError):
        await service.update_profile(
            "principal",
            ProfileUpdate.model_validate({"marketingOptIn": True}, strict=True),
        )
    assert client.write_count == 0
    assert client.store["principal"]["marketing_opt_in"] is False


@pytest.mark.parametrize("corruption", [{"unknown": "must-not-survive-unnoticed"}, {"id": "other-principal"}])
async def test_noncanonical_persisted_shape_fails_closed_without_write(corruption: dict[str, object]) -> None:
    client = Client()
    service = ProfileService(client=cast("Any", client), clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    await service.create_profile("principal", _create())
    client.store["principal"].update(corruption)
    writes = client.write_count

    with pytest.raises(ValueError, match="profile document shape is invalid"):
        await service.get_profile("principal")
    with pytest.raises(ValueError, match="profile document shape is invalid"):
        await service.update_profile(
            "principal",
            ProfileUpdate.model_validate({"marketingOptIn": True}, strict=True),
        )

    assert client.write_count == writes
    assert client.store["principal"]["marketing_opt_in"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contact_email", " Ada@EXAMPLE.COM "),
        ("phone_number", " +358401234567 "),
    ],
)
async def test_noncanonical_persisted_value_fails_closed_without_write(field: str, value: str) -> None:
    client = Client()
    service = ProfileService(client=cast("Any", client), clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    await service.create_profile("principal", _create())
    client.store["principal"][field] = value
    writes = client.write_count

    with pytest.raises(ValueError, match="profile document shape is invalid"):
        await service.get_profile("principal")
    with pytest.raises(ValueError, match="profile document shape is invalid"):
        await service.update_profile(
            "principal",
            ProfileUpdate.model_validate({"marketingOptIn": True}, strict=True),
        )

    assert client.write_count == writes
    assert client.store["principal"][field] == value


async def test_existing_empty_document_is_corruption_not_absence() -> None:
    client = Client()
    client.store["principal"] = {}
    service = ProfileService(client=cast("Any", client), clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))

    with pytest.raises(ValueError, match="profile document shape is invalid"):
        await service.get_profile("principal")
    with pytest.raises(ValueError, match="profile document shape is invalid"):
        await service.update_profile(
            "principal",
            ProfileUpdate.model_validate({"marketingOptIn": True}, strict=True),
        )

    assert client.write_count == 0
    assert client.store["principal"] == {}


async def test_concurrent_deletes_return_one_success_and_one_not_found() -> None:
    client = Client()
    service = ProfileService(client=cast("Any", client), clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    await service.create_profile("principal", _create())
    outcomes = await asyncio.gather(
        service.delete_profile("principal"),
        service.delete_profile("principal"),
        return_exceptions=True,
    )
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(isinstance(outcome, ProfileNotFoundError) for outcome in outcomes) == 1
    assert "principal" not in client.store


async def test_concurrent_patches_are_individually_atomic() -> None:
    client = Client()
    service = ProfileService(client=cast("Any", client), clock=lambda: datetime(2026, 1, 2, tzinfo=UTC))
    await service.create_profile("principal", _create())

    results = await asyncio.gather(
        service.update_profile(
            "principal",
            ProfileUpdate.model_validate({"firstName": "Grace", "marketingOptIn": True}, strict=True),
        ),
        service.update_profile(
            "principal",
            ProfileUpdate.model_validate({"lastName": "Hopper", "phoneNumber": "+12025550123"}, strict=True),
        ),
    )

    assert all(isinstance(result, Profile) for result in results)
    stored = client.store["principal"]
    assert stored["first_name"] == "Grace"
    assert stored["marketing_opt_in"] is True
    assert stored["last_name"] == "Hopper"
    assert stored["phone_number"] == "+12025550123"
    assert client.write_count == 3


async def test_patch_delete_race_never_recreates_the_profile() -> None:
    client = Client()
    service = ProfileService(client=cast("Any", client), clock=lambda: datetime(2026, 1, 2, tzinfo=UTC))
    await service.create_profile("principal", _create())

    patch_result, delete_result = await asyncio.gather(
        service.update_profile(
            "principal",
            ProfileUpdate.model_validate({"marketingOptIn": True}, strict=True),
        ),
        service.delete_profile("principal"),
        return_exceptions=True,
    )

    assert delete_result is None
    assert isinstance(patch_result, Profile | ProfileNotFoundError)
    assert "principal" not in client.store


async def test_known_persistence_failures_are_dependency_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Client()
    service = ProfileService(client=cast("Any", client), clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    failure = google_exceptions.ServiceUnavailable("provider-secret")

    monkeypatch.setattr(Document, "create", AsyncMock(side_effect=failure))
    with pytest.raises(ProfileDependencyError):
        await service.create_profile("principal", _create())
    assert client.write_count == 0

    monkeypatch.setattr(Document, "get", AsyncMock(side_effect=failure))
    with pytest.raises(ProfileDependencyError):
        await service.get_profile("principal")

    monkeypatch.setattr(ProfileService, "_update_in_transaction", AsyncMock(side_effect=failure))
    with pytest.raises(ProfileDependencyError):
        await service.update_profile(
            "principal",
            ProfileUpdate.model_validate({"marketingOptIn": True}, strict=True),
        )

    monkeypatch.setattr(ProfileService, "_delete_in_transaction", AsyncMock(side_effect=failure))
    with pytest.raises(ProfileDependencyError):
        await service.delete_profile("principal")


@pytest.mark.parametrize("operation", ["create", "get", "update", "delete"])
async def test_client_initialization_failures_are_dependency_errors(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_factory = Mock(side_effect=RuntimeError("credential-secret"))
    monkeypatch.setattr("app.services.profile.service.get_async_firestore_client", client_factory)
    service = ProfileService(clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))

    async def invoke_operation() -> None:
        if operation == "create":
            await service.create_profile("principal", _create())
        elif operation == "get":
            await service.get_profile("principal")
        elif operation == "update":
            await service.update_profile(
                "principal",
                ProfileUpdate.model_validate({"marketingOptIn": True}, strict=True),
            )
        else:
            await service.delete_profile("principal")

    with pytest.raises(ProfileDependencyError):
        await invoke_operation()

    client_factory.assert_called_once_with()


async def test_client_initialization_cancellation_is_not_reclassified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.profile.service.get_async_firestore_client",
        Mock(side_effect=asyncio.CancelledError),
    )
    service = ProfileService()

    with pytest.raises(asyncio.CancelledError):
        await service.get_profile("principal")


@pytest.mark.parametrize("failure", [ValueError("unexpected"), asyncio.CancelledError()])
async def test_unexpected_and_cancelled_persistence_failures_propagate(
    failure: BaseException,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Client()
    service = ProfileService(client=cast("Any", client), clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    monkeypatch.setattr(Document, "create", AsyncMock(side_effect=failure))
    with pytest.raises(type(failure)):
        await service.create_profile("principal", _create())
    assert client.write_count == 0


def test_audit_record_contains_no_principal_or_profile_value(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.services.profile.service"):
        _log_profile_audit_event("update")
    record = caplog.records[-1]
    assert record.getMessage() == "Profile mutation committed"
    assert vars(record)["audit"] == {"action": "update", "resource_type": "profile", "result": "success"}
    assert "principal" not in str(vars(record)["audit"])
