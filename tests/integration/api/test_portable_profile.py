"""Real FastAPI boundary tests for the authenticated GCP profile contract."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, call

import cbor2
import httpx2
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth.firebase import FirebaseUser, verify_firebase_token
from app.exceptions import ProfileAlreadyExistsError, ProfileDependencyError, ProfileNotFoundError
from app.models.profile import Profile


def _profile(*, marketing: bool = False, identifier: str = "test-user-123") -> Profile:
    return Profile.model_validate(
        {
            "id": identifier,
            "firstName": "Ada",
            "lastName": "Lovelace",
            "contactEmail": "Ada@example.com",
            "phoneNumber": "+358401234567",
            "marketingOptIn": marketing,
            "termsAccepted": True,
            "createdAt": datetime(2026, 7, 30, 12, 0, tzinfo=UTC),
            "updatedAt": datetime(
                2026,
                7,
                30,
                12,
                0,
                tzinfo=UTC,
                microsecond=int(marketing) * 1000,
            ),
        },
        strict=True,
    )


def _create_body() -> dict[str, object]:
    return {
        "firstName": "Ada",
        "lastName": "Lovelace",
        "contactEmail": " Ada@EXAMPLE.COM ",
        "phoneNumber": " +358401234567 ",
        "termsAccepted": True,
    }


def _assert_problem(response: httpx2.Response, status: int, code: str) -> dict[str, object]:
    assert response.status_code == status
    assert response.headers["Content-Type"].split(";", maxsplit=1)[0] == "application/problem+json"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"]
    body = response.json()
    assert body["status"] == status
    assert body["code"] == code
    return body


def test_profile_common_policy_precedes_authentication(
    client: TestClient,
    mock_profile_service: AsyncMock,
) -> None:
    _assert_problem(client.get("/v1/profile?other=1"), 400, "invalid_request")
    _assert_problem(client.get("/v1/profile", headers={"Accept": "text/plain"}), 406, "not_acceptable")
    _assert_problem(
        client.post(
            "/v1/profile",
            content=b"x",
            headers={"Content-Length": "1000001", "Content-Type": "application/json"},
        ),
        413,
        "payload_too_large",
    )
    _assert_problem(
        client.patch(
            "/v1/profile",
            content=b"x",
            headers={"Content-Length": "1000001", "Content-Type": "application/json"},
        ),
        413,
        "payload_too_large",
    )
    mock_profile_service.assert_not_called()


@pytest.mark.parametrize(
    ("method", "document", "success_status", "service_method"),
    [
        ("POST", _create_body(), 201, "create_profile"),
        ("PATCH", {"marketingOptIn": True}, 200, "update_profile"),
    ],
)
@pytest.mark.parametrize("size", [999_999, 1_000_000, 1_000_001])
def test_profile_writes_enforce_each_streamed_body_boundary(
    client: TestClient,
    with_fake_user: None,
    mock_profile_service: AsyncMock,
    method: str,
    document: dict[str, object],
    success_status: int,
    service_method: str,
    size: int,
) -> None:
    del with_fake_user
    import json

    prefix = json.dumps(document, separators=(",", ":")).encode()
    payload = prefix + b" " * (size - len(prefix))
    selected_method = getattr(mock_profile_service, service_method)
    selected_method.return_value = _profile(marketing=method == "PATCH")
    response = client.request(
        method,
        "/v1/profile",
        content=payload,
        headers={"Authorization": "ignored", "Content-Type": "application/json"},
    )
    if size <= 1_000_000:
        assert response.status_code == success_status
        selected_method.assert_awaited_once()
    else:
        _assert_problem(response, 413, "payload_too_large")
        selected_method.assert_not_awaited()


def test_profile_authentication_precedes_body_decoding(client: TestClient, mock_profile_service: AsyncMock) -> None:
    for headers in (
        {},
        {"Authorization": "Basic value"},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer\ttoken"},
        {"Authorization": "Bearer first, Bearer second"},
    ):
        response = client.post(
            "/v1/profile",
            content=b'{"broken":',
            headers={**headers, "Content-Type": "application/json"},
        )
        _assert_problem(response, 401, "unauthorized")
        assert response.headers["WWW-Authenticate"] == "Bearer"
    mock_profile_service.assert_not_called()


def test_profile_create_get_patch_delete_wire_contract(
    client: TestClient,
    with_fake_user: None,
    mock_profile_service: AsyncMock,
) -> None:
    del with_fake_user
    created_profile = _profile()
    mock_profile_service.create_profile.return_value = created_profile
    created = client.post("/v1/profile", json=_create_body(), headers={"Authorization": "ignored"})
    assert created.status_code == 201
    assert created.headers["Location"] == "/v1/profile"
    assert created.json() == {
        "id": "test-user-123",
        "firstName": "Ada",
        "lastName": "Lovelace",
        "contactEmail": "Ada@example.com",
        "phoneNumber": "+358401234567",
        "marketingOptIn": False,
        "termsAccepted": True,
        "createdAt": "2026-07-30T12:00:00.000Z",
        "updatedAt": "2026-07-30T12:00:00.000Z",
    }
    user_id, create_model = mock_profile_service.create_profile.await_args.args
    assert user_id == "test-user-123"
    assert create_model.contact_email == "Ada@example.com"
    assert create_model.phone_number == "+358401234567"
    assert create_model.marketing_opt_in is False

    mock_profile_service.get_profile.return_value = created_profile
    fetched = client.get("/v1/profile", headers={"Authorization": "ignored", "Accept": "application/cbor"})
    assert fetched.status_code == 200
    assert cbor2.loads(fetched.content)["id"] == "test-user-123"

    changed = _profile(marketing=True)
    mock_profile_service.update_profile.return_value = changed
    patched = client.patch(
        "/v1/profile",
        content=cbor2.dumps({"marketingOptIn": True}),
        headers={"Authorization": "ignored", "Content-Type": "application/cbor"},
    )
    assert patched.status_code == 200
    assert patched.json()["marketingOptIn"] is True
    assert patched.json()["updatedAt"] == "2026-07-30T12:00:00.001Z"
    assert mock_profile_service.update_profile.await_args.args[1].marketing_opt_in is True

    deleted = client.delete(
        "/v1/profile",
        headers={"Authorization": "ignored", "Accept": "text/plain"},
    )
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert "Content-Type" not in deleted.headers
    assert "Content-Length" not in deleted.headers
    assert deleted.headers["Cache-Control"] == "no-store"
    mock_profile_service.delete_profile.assert_awaited_once_with("test-user-123")


def test_each_authenticated_principal_selects_only_its_own_profile(
    client: TestClient,
    mock_profile_service: AsyncMock,
) -> None:
    from app.main import fastapi_app

    async def current_principal(request: Request) -> FirebaseUser:
        return FirebaseUser(uid=request.headers["Authorization"].removeprefix("Bearer "))

    async def selected_profile(user_id: str) -> Profile:
        return _profile(identifier=user_id)

    fastapi_app.dependency_overrides[verify_firebase_token] = current_principal
    mock_profile_service.get_profile.side_effect = selected_profile
    try:
        first = client.get("/v1/profile", headers={"Authorization": "Bearer principal-a"})
        second = client.get("/v1/profile", headers={"Authorization": "Bearer principal-b"})
    finally:
        fastapi_app.dependency_overrides.pop(verify_firebase_token, None)

    assert first.status_code == 200
    assert first.json()["id"] == "principal-a"
    assert second.status_code == 200
    assert second.json()["id"] == "principal-b"
    mock_profile_service.get_profile.assert_has_awaits([call("principal-a"), call("principal-b")])


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"marketingOptIn": None},
        {"termsAccepted": True},
        {"marketing_opt_in": True},
        {"unknown": "secret-value"},
    ],
)
def test_profile_patch_validation_is_closed_nonempty_and_side_effect_free(
    client: TestClient,
    with_fake_user: None,
    mock_profile_service: AsyncMock,
    body: dict[str, object],
) -> None:
    del with_fake_user
    response = client.patch("/v1/profile", json=body, headers={"Authorization": "ignored"})
    problem = _assert_problem(response, 422, "validation_failed")
    assert "secret-value" not in str(problem)
    assert "unknown" not in str(problem)
    mock_profile_service.update_profile.assert_not_awaited()


def test_profile_duplicate_json_is_400_without_persistence(
    client: TestClient,
    with_fake_user: None,
    mock_profile_service: AsyncMock,
) -> None:
    del with_fake_user
    response = client.patch(
        "/v1/profile",
        content=b'{"firstName":"Ada","firstName":"Grace"}',
        headers={"Authorization": "ignored", "Content-Type": "application/json"},
    )
    _assert_problem(response, 400, "invalid_request")
    mock_profile_service.update_profile.assert_not_awaited()


@pytest.mark.parametrize(
    ("method", "service_method", "error", "status", "code"),
    [
        ("post", "create_profile", ProfileAlreadyExistsError(), 409, "profile_exists"),
        ("get", "get_profile", ProfileNotFoundError(), 404, "profile_not_found"),
        ("patch", "update_profile", ProfileNotFoundError(), 404, "profile_not_found"),
        ("delete", "delete_profile", ProfileNotFoundError(), 404, "profile_not_found"),
        ("get", "get_profile", ProfileDependencyError(), 503, "dependency_unavailable"),
    ],
)
def test_profile_service_outcomes_map_to_exact_safe_problems(
    client: TestClient,
    with_fake_user: None,
    mock_profile_service: AsyncMock,
    method: str,
    service_method: str,
    error: Exception,
    status: int,
    code: str,
) -> None:
    del with_fake_user
    getattr(mock_profile_service, service_method).side_effect = error
    kwargs: dict[str, object] = {"headers": {"Authorization": "ignored"}}
    if method == "post":
        kwargs["json"] = _create_body()
    elif method == "patch":
        kwargs["json"] = {"marketingOptIn": True}
    response = getattr(client, method)("/v1/profile", **kwargs)
    _assert_problem(response, status, code)
    if status == 503:
        assert "Retry-After" not in response.headers


def test_profile_method_allow_is_complete(client: TestClient) -> None:
    response = client.put("/v1/profile", content=b"not-read")
    _assert_problem(response, 405, "method_not_allowed")
    assert response.headers["Allow"] == "DELETE, GET, PATCH, POST"
