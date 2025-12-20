"""Integration/API tests using TestClient against the app."""

from fastapi.testclient import TestClient

from tests.helpers.profiles import make_profile_payload_dict


def test_root_endpoint(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Hello World"
    assert data["docs"] == "/api-docs"


def test_health_check(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}


def test_unauthorized_access(client: TestClient) -> None:
    # Create
    payload = make_profile_payload_dict()
    assert client.post("/profile/", json=payload).status_code == 401
    # Get
    assert client.get("/profile/").status_code == 401
    # Update
    assert client.put("/profile/", json={}).status_code == 401
    # Delete
    assert client.delete("/profile/").status_code == 401


def test_oversized_request_body_is_rejected(client: TestClient) -> None:
    """Requests exceeding MAX_REQUEST_SIZE_BYTES should get 413."""
    big = "x" * (2_000_000)
    res = client.post("/", content=big, headers={"Content-Type": "application/octet-stream"})
    assert res.status_code == 413
    assert res.json()["detail"].lower().startswith("request body too large")
