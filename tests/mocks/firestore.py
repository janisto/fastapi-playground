"""
Fake Firestore classes for unit tests.
"""

from typing import Any


class FakeDocumentSnapshot:
    """
    Fake Firestore document snapshot.
    """

    def __init__(self, data: dict[str, Any] | None, doc_id: str = "test-id") -> None:
        self._data = data
        self.id = doc_id
        self.exists = data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return self._data


class FakeDocumentReference:
    """
    Fake Firestore document reference.
    """

    def __init__(self, store: dict[str, dict[str, Any]], doc_id: str) -> None:
        self._store = store
        self.id = doc_id

    async def get(self) -> FakeDocumentSnapshot:
        data = self._store.get(self.id)
        return FakeDocumentSnapshot(data, self.id)

    async def set(self, data: dict[str, Any]) -> None:
        self._store[self.id] = data

    async def update(self, data: dict[str, Any]) -> None:
        if self.id in self._store:
            self._store[self.id].update(data)
        else:
            self._store[self.id] = data

    async def delete(self) -> None:
        self._store.pop(self.id, None)


class FakeCollection:
    """
    Fake Firestore collection.
    """

    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self._store = store

    def document(self, doc_id: str) -> FakeDocumentReference:
        return FakeDocumentReference(self._store, doc_id)


class FakeTransaction:
    """
    Fake Firestore transaction for unit tests.

    Provides minimal transaction semantics for testing transactional code.
    """

    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self._store = store

    async def get(self, doc_ref: FakeDocumentReference) -> FakeDocumentSnapshot:
        data = self._store.get(doc_ref.id)
        return FakeDocumentSnapshot(data, doc_ref.id)

    def set(self, doc_ref: FakeDocumentReference, data: dict[str, Any]) -> None:
        self._store[doc_ref.id] = data

    def update(self, doc_ref: FakeDocumentReference, data: dict[str, Any]) -> None:
        if doc_ref.id in self._store:
            self._store[doc_ref.id].update(data)
        else:
            self._store[doc_ref.id] = data

    def delete(self, doc_ref: FakeDocumentReference) -> None:
        self._store.pop(doc_ref.id, None)


class FakeAsyncClient:
    """
    Fake async Firestore client for unit tests.

    Usage:
        @pytest.fixture
        def fake_db(monkeypatch: pytest.MonkeyPatch) -> FakeAsyncClient:
            db = FakeAsyncClient()
            monkeypatch.setattr("app.services.profile.get_async_firestore_client", lambda: db)
            return db
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self._store)

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self._store)

    def clear(self) -> None:
        """
        Clear all stored data (useful for test cleanup).
        """
        self._store.clear()
