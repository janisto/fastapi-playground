from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import app


class DummyUser:
    def __init__(self, uid: str) -> None:
        self.uid = uid


@pytest.fixture(autouse=True)
def patch_user(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    async def fake_verify(token: str) -> DummyUser:  # type: ignore[unused-ignore]
        return DummyUser("user-err")

    monkeypatch.setattr("app.routers.profile.verify_firebase_token", fake_verify)
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test"}


def test_create_profile_conflict(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    # Simulate existing profile by having service return object on get_profile
    class Obj:
        pass

    async def fake_get(uid: str) -> object | None:
        return Obj()

    monkeypatch.setattr("app.routers.profile.profile_service.get_profile", fake_get)
    resp = client.post(
        "/profile/",
        headers=_auth_headers(),
        json={
            "firstname": "A",
            "lastname": "B",
            "email": "a@b.com",
            "phone_number": "+123456789",
            "marketing": True,
            "terms": True,
        },
    )
    assert resp.status_code == 409


def test_get_profile_not_found(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    async def fake_get(uid: str) -> None:
        return None

    monkeypatch.setattr("app.routers.profile.profile_service.get_profile", fake_get)
    resp = client.get("/profile/", headers=_auth_headers())
    assert resp.status_code == 404


def test_update_profile_not_found(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    async def fake_update(uid: str, data: dict) -> None:
        return None

    monkeypatch.setattr("app.routers.profile.profile_service.update_profile", fake_update)
    resp = client.put("/profile/", headers=_auth_headers(), json={})
    assert resp.status_code == 404


def test_delete_profile_not_found(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    async def fake_delete(uid: str) -> bool:
        return False

    monkeypatch.setattr("app.routers.profile.profile_service.delete_profile", fake_delete)
    resp = client.delete("/profile/", headers=_auth_headers())
    assert resp.status_code == 404


def test_create_profile_internal_error(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    async def fake_get(uid: str) -> None:
        return None

    async def fake_create(uid: str, data: dict) -> None:  # type: ignore[unused-ignore]
        raise RuntimeError("boom")

    monkeypatch.setattr("app.routers.profile.profile_service.get_profile", fake_get)
    monkeypatch.setattr("app.routers.profile.profile_service.create_profile", fake_create)

    resp = client.post(
        "/profile/",
        headers=_auth_headers(),
        json={
            "firstname": "A",
            "lastname": "B",
            "email": "a@b.com",
            "phone_number": "+123456789",
            "marketing": True,
            "terms": True,
        },
    )
    assert resp.status_code == 500
