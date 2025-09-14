from unittest.mock import MagicMock

import pytest

from app.models.profile import ProfileCreate, ProfileUpdate
from app.services.profile import ProfileService


def _fake_doc(data: dict | None, exists: bool = True) -> MagicMock:  # helper to mimic Firestore document snapshots
    snap = MagicMock()
    snap.exists = exists
    snap.to_dict.return_value = data
    return snap


class _DocRef:
    def __init__(self, store: dict[str, dict], key: str) -> None:
        self._store = store
        self._key = key

    def get(self) -> MagicMock:
        if self._key in self._store:
            return _fake_doc(self._store[self._key])
        return _fake_doc(None, exists=False)

    def set(self, data: dict) -> None:
        self._store[self._key] = data

    def update(self, data: dict) -> None:
        self._store[self._key].update(data)

    def delete(self) -> None:
        self._store.pop(self._key, None)


class _Collection:
    def __init__(self, store: dict[str, dict]) -> None:
        self._store = store

    def document(self, key: str) -> _DocRef:
        return _DocRef(self._store, key)


class _FakeDB:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def collection(self, name: str) -> _Collection:  # name ignored in fake
        return _Collection(self._store)


@pytest.fixture()
def service() -> ProfileService:
    return ProfileService()


@pytest.fixture()
def fake_db(monkeypatch: pytest.MonkeyPatch) -> _FakeDB:
    db = _FakeDB()
    monkeypatch.setattr("app.services.profile.get_firestore_client", lambda: db)
    return db


def _sample_create(**overrides: object) -> ProfileCreate:
    base = dict(
        firstname="John",
        lastname="Doe",
        email="john@example.com",
        phone_number="+123456789",
        marketing=True,
        terms=True,
    )
    base.update(overrides)
    return ProfileCreate(**base)


@pytest.mark.asyncio
async def test_create_profile_success(service: ProfileService, fake_db: _FakeDB) -> None:
    data = _sample_create()
    profile = await service.create_profile("user1", data)
    assert profile.id == "user1"
    assert fake_db._store["user1"]["firstname"] == "John"


@pytest.mark.asyncio
async def test_create_profile_duplicate(service: ProfileService, fake_db: _FakeDB) -> None:
    data = _sample_create()
    await service.create_profile("user1", data)
    with pytest.raises(ValueError):
        await service.create_profile("user1", data)


@pytest.mark.asyncio
async def test_get_profile_not_found(service: ProfileService, fake_db: _FakeDB) -> None:
    result = await service.get_profile("missing")
    assert result is None


@pytest.mark.asyncio
async def test_update_profile_no_changes_returns_existing(service: ProfileService, fake_db: _FakeDB) -> None:
    data = _sample_create()
    await service.create_profile("user1", data)
    original = await service.get_profile("user1")
    updated = await service.update_profile("user1", ProfileUpdate())
    assert updated == original


@pytest.mark.asyncio
async def test_update_profile_changes(service: ProfileService, fake_db: _FakeDB) -> None:
    data = _sample_create()
    await service.create_profile("user1", data)
    updated = await service.update_profile("user1", ProfileUpdate(firstname="Jane", marketing=False))
    assert updated is not None
    assert updated.firstname == "Jane"
    assert updated.marketing is False


@pytest.mark.asyncio
async def test_update_profile_missing(service: ProfileService, fake_db: _FakeDB) -> None:
    result = await service.update_profile("missing", ProfileUpdate(firstname="X"))
    assert result is None


@pytest.mark.asyncio
async def test_delete_profile_success(service: ProfileService, fake_db: _FakeDB) -> None:
    await service.create_profile("user1", _sample_create())
    ok = await service.delete_profile("user1")
    assert ok is True
    assert "user1" not in fake_db._store


@pytest.mark.asyncio
async def test_delete_profile_missing(service: ProfileService, fake_db: _FakeDB) -> None:
    ok = await service.delete_profile("missing")
    assert ok is False
