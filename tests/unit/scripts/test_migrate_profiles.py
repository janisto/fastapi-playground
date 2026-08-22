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

    def document(self, identifier: str) -> Reference:
        return Reference(identifier)


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
        self.create_calls: list[tuple[object, dict[str, object]]] = []
        self.delete_calls: list[object] = []

    def set(self, document: object, replacement: dict[str, object]) -> None:
        self.set_calls.append((document, replacement))

    def create(self, document: object, replacement: dict[str, object]) -> None:
        self.create_calls.append((document, replacement))

    def delete(self, document: object) -> None:
        self.delete_calls.append(document)


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


async def test_retired_document_rejects_inverted_timestamps_before_truncation_without_writing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_at = datetime(2026, 7, 30, 12, 0, 0, 123900, tzinfo=UTC)
    updated_at = datetime(2026, 7, 30, 12, 0, 0, 123100, tzinfo=UTC)
    document = {**_retired(), "created_at": created_at, "updated_at": updated_at}
    client = Client([Snapshot("principal", document)])
    replacement = _install_client(monkeypatch, client)

    with pytest.raises(ValueError, match="updated timestamp predates creation"):
        await migrate_profiles.migrate(apply=True)

    replacement.assert_not_awaited()


async def test_dry_run_validates_without_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client([Snapshot("principal", _retired()), Snapshot("canonical", _canonical("canonical"))])
    replacement = _install_client(monkeypatch, client)

    assert await migrate_profiles.migrate(apply=False) == (2, 1, 0)
    replacement.assert_not_awaited()


async def test_dry_run_marks_legacy_storage_key_for_rewrite(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client([Snapshot("~principal", _canonical("~principal"))])
    replacement = _install_client(monkeypatch, client)

    assert await migrate_profiles.migrate(apply=False) == (1, 1, 0)
    replacement.assert_not_awaited()


async def test_apply_rekeys_legacy_storage_key_without_changing_public_id(monkeypatch: pytest.MonkeyPatch) -> None:
    source = Snapshot("~principal", _canonical("~principal"))
    client = Client([source])
    replacement = _install_client(monkeypatch, client)

    assert await migrate_profiles.migrate(apply=True) == (1, 1, 1)
    replacement.assert_awaited_once()
    assert replacement.await_args is not None
    transaction, actual_source, target, expected, canonical = replacement.await_args.args
    assert transaction is client.transaction_value
    assert actual_source is source.reference
    assert target.id == "~fnByaW5jaXBhbA"
    assert expected == canonical == _canonical("~principal")


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
        None,
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
    await _REPLACE_BODY(matching, document, None, expected, replacement)
    assert matching.set_calls == [(document, replacement)]
    assert matching.create_calls == []
    assert matching.delete_calls == []

    for current in (None, {**expected, "first_name": "Changed"}):
        transaction = ReplacementTransaction()
        changed_document = ReplacementDocument(ReplacementSnapshot(current))
        with pytest.raises(RuntimeError, match="profile changed during migration"):
            await _REPLACE_BODY(transaction, changed_document, None, expected, replacement)
        assert transaction.set_calls == []


async def test_compare_before_write_rekeys_only_when_target_is_absent() -> None:
    expected = _canonical("~principal")
    source = ReplacementDocument(ReplacementSnapshot(expected))
    target = ReplacementDocument(ReplacementSnapshot(None))
    transaction = ReplacementTransaction()

    await _REPLACE_BODY(transaction, source, target, expected, expected)

    assert transaction.set_calls == []
    assert transaction.create_calls == [(target, expected)]
    assert transaction.delete_calls == [source]

    occupied = ReplacementDocument(ReplacementSnapshot(_canonical("other")))
    transaction = ReplacementTransaction()
    with pytest.raises(RuntimeError, match="profile storage target already exists"):
        await _REPLACE_BODY(transaction, source, occupied, expected, expected)
    assert transaction.set_calls == []
    assert transaction.create_calls == []
    assert transaction.delete_calls == []


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
