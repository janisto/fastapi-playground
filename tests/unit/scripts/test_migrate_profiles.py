"""Dry-run-first profile migration tests."""

from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from google.api_core.datetime_helpers import DatetimeWithNanoseconds

from scripts import migrate_profiles

_CREATED = datetime(2026, 7, 30, 12, 0, 0, 123000, tzinfo=UTC)
_UPDATED = datetime(2026, 7, 31, 12, 0, 0, 456000, tzinfo=UTC)
_REPLACE_BODY = cast("Any", migrate_profiles._replace_document).to_wrap


def _retired(identifier: str = "principal") -> dict[str, object]:
    return {
        "id": identifier,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "Ada@EXAMPLE.COM",
        "phone_number": "+358401234567",
        "marketing": False,
        "terms": True,
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    }


def _canonical(identifier: str = "principal") -> dict[str, object]:
    return {
        "id": identifier,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "contact_email": "Ada@example.com",
        "phone_number": "+358401234567",
        "marketing_opt_in": False,
        "terms_accepted": True,
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    }


class Reference:
    def __init__(self, identifier: str) -> None:
        self.id = identifier


class Snapshot:
    def __init__(self, identifier: str, data: dict[str, object]) -> None:
        self.reference = Reference(identifier)
        self._data = data

    def to_dict(self) -> dict[str, object]:
        return dict(self._data)


class Collection:
    def __init__(self, snapshots: list[Snapshot]) -> None:
        self._snapshots = snapshots

    async def stream(self) -> Any:
        for snapshot in self._snapshots:
            yield snapshot


class Client:
    def __init__(self, snapshots: list[Snapshot]) -> None:
        self._snapshots = snapshots
        self.transaction_value = object()

    def collection(self, name: str) -> Collection:
        assert name == "profiles"
        return Collection(self._snapshots)

    def transaction(self) -> object:
        return self.transaction_value


class ReplacementTransaction:
    def __init__(self) -> None:
        self.set_calls: list[tuple[object, dict[str, object]]] = []

    def set(self, document: object, replacement: dict[str, object]) -> None:
        self.set_calls.append((document, replacement))


class ReplacementSnapshot:
    def __init__(self, data: dict[str, object] | None) -> None:
        self.exists = data is not None
        self._data = data

    def to_dict(self) -> dict[str, object] | None:
        return None if self._data is None else dict(self._data)


class ReplacementDocument:
    def __init__(self, snapshot: ReplacementSnapshot) -> None:
        self.snapshot = snapshot

    async def get(self, *, transaction: object) -> ReplacementSnapshot:
        del transaction
        return self.snapshot


def _install_client(monkeypatch: pytest.MonkeyPatch, client: Client) -> AsyncMock:
    replacement = AsyncMock()
    monkeypatch.setattr(migrate_profiles, "initialize_firebase", lambda: None)
    monkeypatch.setattr(migrate_profiles, "get_async_firestore_client", lambda: client)
    monkeypatch.setattr(migrate_profiles, "_replace_document", replacement)
    return replacement


def test_retired_document_maps_to_exact_canonical_persistence_shape() -> None:
    assert migrate_profiles._canonical_document(_retired()) == _canonical()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contact_email", " Ada@EXAMPLE.COM "),
        ("phone_number", " +358401234567 "),
    ],
)
def test_canonical_document_rejects_values_that_require_normalization(field: str, value: str) -> None:
    document = {**_canonical(), field: value}

    with pytest.raises(ValueError, match="canonical profile values are invalid"):
        migrate_profiles._validate_canonical_document(document)


def test_canonical_document_rejects_hidden_firestore_submillisecond_precision() -> None:
    document = {
        **_canonical(),
        "updated_at": DatetimeWithNanoseconds(
            2026,
            7,
            31,
            12,
            0,
            tzinfo=UTC,
            nanosecond=456_000_001,
        ),
    }

    with pytest.raises(ValueError, match="whole-millisecond precision"):
        migrate_profiles._validate_canonical_document(document)


async def test_dry_run_validates_without_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client([Snapshot("principal", _retired()), Snapshot("canonical", _canonical("canonical"))])
    replacement = _install_client(monkeypatch, client)

    assert await migrate_profiles.migrate(apply=False) == (2, 1, 0)
    replacement.assert_not_awaited()


async def test_dry_run_aborts_instead_of_approving_noncanonical_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Client([Snapshot("principal", {**_canonical(), "contact_email": " Ada@EXAMPLE.COM "})])
    replacement = _install_client(monkeypatch, client)

    with pytest.raises(ValueError, match="canonical profile values are invalid"):
        await migrate_profiles.migrate(apply=False)
    replacement.assert_not_awaited()


async def test_apply_writes_only_retired_documents_and_canonical_rerun_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retired = _retired()
    reference = Snapshot("principal", retired)
    client = Client([reference, Snapshot("canonical", _canonical("canonical"))])
    replacement = _install_client(monkeypatch, client)

    assert await migrate_profiles.migrate(apply=True) == (2, 1, 1)
    replacement.assert_awaited_once_with(
        client.transaction_value,
        reference.reference,
        retired,
        _canonical(),
    )

    canonical_client = Client([Snapshot("principal", _canonical())])
    replacement = _install_client(monkeypatch, canonical_client)
    assert await migrate_profiles.migrate(apply=True) == (1, 0, 0)
    replacement.assert_not_awaited()


async def test_compare_before_write_rejects_missing_or_changed_document() -> None:
    expected = _retired()
    replacement = _canonical()

    matching = ReplacementTransaction()
    document = ReplacementDocument(ReplacementSnapshot(expected))
    await _REPLACE_BODY(matching, document, expected, replacement)
    assert matching.set_calls == [(document, replacement)]

    for current in (None, {**expected, "first_name": "Changed"}):
        transaction = ReplacementTransaction()
        changed_document = ReplacementDocument(ReplacementSnapshot(current))
        with pytest.raises(RuntimeError, match="profile changed during migration"):
            await _REPLACE_BODY(transaction, changed_document, expected, replacement)
        assert transaction.set_calls == []


@pytest.mark.parametrize(
    "invalid",
    [
        Snapshot("different-principal", _retired()),
        Snapshot("principal", {**_retired(), "unknown": True}),
        Snapshot("principal", {**_retired(), "terms": False}),
    ],
)
async def test_invalid_candidate_aborts_before_any_write(
    invalid: Snapshot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Client([Snapshot("valid", _retired("valid")), invalid])
    replacement = _install_client(monkeypatch, client)
    with pytest.raises(ValueError, match=r"(?:profile|Profile)"):
        await migrate_profiles.migrate(apply=True)
    replacement.assert_not_awaited()
