"""Real FastAPI boundary tests for the public GitHub operation family."""

from unittest.mock import AsyncMock

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.auth.firebase import verify_firebase_token
from app.core.problems import PortableProblem
from app.models.github import (
    GitHubActivityPage,
    GitHubLanguages,
    GitHubOwner,
    GitHubRepository,
    GitHubRepositoryPage,
    GitHubTagPage,
)


def _owner() -> GitHubOwner:
    return GitHubOwner.model_validate(
        {
            "id": 1,
            "login": "octocat",
            "type": "User",
            "name": None,
            "avatarUrl": "https://avatars.example/octocat",
            "htmlUrl": "https://github.example/octocat",
            "company": None,
            "blog": None,
            "location": None,
            "bio": None,
            "publicRepos": 2,
            "followers": 3,
            "following": 4,
            "createdAt": "2020-01-01T00:00:00.000Z",
            "updatedAt": "2020-01-02T00:00:00.000Z",
        },
        strict=True,
    )


def _repository() -> GitHubRepository:
    return GitHubRepository.model_validate(
        {
            "id": 2,
            "name": "repo",
            "fullName": "octocat/repo",
            "description": None,
            "htmlUrl": "https://github.example/octocat/repo",
            "fork": False,
            "language": None,
            "stargazersCount": 5,
            "forksCount": 1,
            "openIssuesCount": 0,
            "archived": False,
            "createdAt": "2020-01-01T00:00:00.000Z",
            "updatedAt": "2020-01-02T00:00:00.000Z",
            "pushedAt": None,
            "defaultBranch": "main",
            "license": None,
            "topics": [],
            "disabled": False,
        },
        strict=True,
    )


def _assert_problem(response: httpx2.Response, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.json()["code"] == code
    assert response.json()["status"] == status
    assert response.headers["Cache-Control"] == "no-store"


def test_owner_and_repository_are_public_closed_projections(
    client: TestClient,
    mock_github_service: AsyncMock,
) -> None:
    from app.main import fastapi_app

    verifier = AsyncMock(side_effect=AssertionError("public route authenticated"))
    fastapi_app.dependency_overrides[verify_firebase_token] = verifier
    mock_github_service.get_owner.return_value = _owner()
    mock_github_service.get_repository.return_value = _repository()

    owner = client.get(
        "/v1/github/owners/octocat",
        headers={"Authorization": "Bearer inbound-secret", "Cookie": "session=secret"},
    )
    assert owner.status_code == 200
    assert owner.json() == _owner().model_dump(mode="json", by_alias=True)
    assert "email" not in owner.json()

    repository = client.get("/v1/github/repos/octocat/repo", headers={"Accept": "application/cbor"})
    assert repository.status_code == 200
    assert repository.headers["Content-Type"] == "application/cbor"
    mock_github_service.get_repository.assert_awaited_once_with("octocat", "repo")
    verifier.assert_not_awaited()


def test_paginated_routes_reconstruct_only_relative_public_links(
    client: TestClient,
    mock_github_service: AsyncMock,
) -> None:
    mock_github_service.list_owner_repositories.return_value = (
        GitHubRepositoryPage(repos=[], count=0),
        "next-cursor",
        None,
    )
    response = client.get(
        "/v1/github/owners/octocat/repos?limit=1",
        headers={"Host": "attacker.example"},
    )
    assert response.status_code == 200
    assert response.json() == {"repos": [], "count": 0}
    assert response.headers["Link"].startswith("</v1/github/owners/octocat/repos?")
    assert "limit=1" in response.headers["Link"]
    assert "cursor=next-cursor" in response.headers["Link"]
    mock_github_service.list_owner_repositories.assert_awaited_once_with("octocat", 1, None)

    mock_github_service.list_repository_activity.return_value = (
        GitHubActivityPage(activities=[], count=0),
        None,
        "previous",
    )
    activity = client.get("/v1/github/repos/octocat/repo/activity?limit=100&cursor=current")
    assert activity.status_code == 200
    assert 'rel="prev"' in activity.headers["Link"]

    mock_github_service.list_repository_tags.return_value = (GitHubTagPage(tags=[], count=0), None, None)
    tags = client.get("/v1/github/repos/octocat/repo/tags")
    assert tags.status_code == 200
    assert "Link" not in tags.headers


@pytest.mark.parametrize(
    ("target", "service_method", "expected_arguments"),
    [
        ("/v1/github/owners/octocat/repos", "list_owner_repositories", ("octocat", 20, None)),
        ("/v1/github/owners/octocat/repos?limit=1", "list_owner_repositories", ("octocat", 1, None)),
        ("/v1/github/owners/octocat/repos?limit=100", "list_owner_repositories", ("octocat", 100, None)),
        (
            "/v1/github/repos/octocat/repo/activity",
            "list_repository_activity",
            ("octocat", "repo", 20, None),
        ),
        (
            "/v1/github/repos/octocat/repo/activity?limit=1",
            "list_repository_activity",
            ("octocat", "repo", 1, None),
        ),
        (
            "/v1/github/repos/octocat/repo/activity?limit=100",
            "list_repository_activity",
            ("octocat", "repo", 100, None),
        ),
        ("/v1/github/repos/octocat/repo/tags", "list_repository_tags", ("octocat", "repo", 20, None)),
        ("/v1/github/repos/octocat/repo/tags?limit=1", "list_repository_tags", ("octocat", "repo", 1, None)),
        (
            "/v1/github/repos/octocat/repo/tags?limit=100",
            "list_repository_tags",
            ("octocat", "repo", 100, None),
        ),
    ],
)
def test_every_github_collection_accepts_default_and_limit_boundaries(
    client: TestClient,
    mock_github_service: AsyncMock,
    target: str,
    service_method: str,
    expected_arguments: tuple[object, ...],
) -> None:
    method = getattr(mock_github_service, service_method)
    if service_method == "list_owner_repositories":
        method.return_value = (GitHubRepositoryPage(repos=[], count=0), None, None)
    elif service_method == "list_repository_activity":
        method.return_value = (GitHubActivityPage(activities=[], count=0), None, None)
    else:
        method.return_value = (GitHubTagPage(tags=[], count=0), None, None)

    response = client.get(target)

    assert response.status_code == 200
    method.assert_awaited_once_with(*expected_arguments)


def test_languages_exact_empty_shape(client: TestClient, mock_github_service: AsyncMock) -> None:
    mock_github_service.list_repository_languages.return_value = GitHubLanguages(languages=[])
    response = client.get("/v1/github/repos/octocat/repo/languages")
    assert response.status_code == 200
    assert response.json() == {"languages": []}


@pytest.mark.parametrize(
    "target",
    [
        "/v1/github/owners/-bad",
        "/v1/github/owners/bad-",
        "/v1/github/owners/å",
        "/v1/github/repos/octocat/repo!",
    ],
)
def test_invalid_path_is_422_without_fetch(
    client: TestClient,
    mock_github_service: AsyncMock,
    target: str,
) -> None:
    _assert_problem(client.get(target), 422, "validation_failed")
    mock_github_service.assert_not_called()
    for method in (
        mock_github_service.get_owner,
        mock_github_service.get_repository,
        mock_github_service.list_repository_activity,
    ):
        method.assert_not_awaited()


def test_dot_only_repository_error_is_source_free_without_fetch(
    client: TestClient,
    mock_github_service: AsyncMock,
) -> None:
    response = client.get("/v1/github/repos/octocat/....")
    _assert_problem(response, 422, "validation_failed")
    assert response.json()["errors"] == [{"detail": "Request field is invalid"}]
    mock_github_service.assert_not_called()


@pytest.mark.parametrize(
    ("query", "status", "code"),
    [
        ("unknown=1", 400, "invalid_request"),
        ("limit=1&limit=2", 400, "invalid_request"),
        ("cursor=", 400, "invalid_request"),
        ("cursor=%FF", 400, "invalid_request"),
        ("limit=x", 422, "validation_failed"),
        ("limit=0", 422, "validation_failed"),
        ("limit=101", 422, "validation_failed"),
        (f"limit={'9' * 5000}", 422, "validation_failed"),
    ],
)
def test_github_closed_query_and_limit_split_without_fetch(
    client: TestClient,
    mock_github_service: AsyncMock,
    query: str,
    status: int,
    code: str,
) -> None:
    _assert_problem(client.get(f"/v1/github/owners/octocat/repos?{query}"), status, code)
    mock_github_service.list_owner_repositories.assert_not_awaited()


def test_point_query_negotiation_and_method_reject_before_fetch(
    client: TestClient,
    mock_github_service: AsyncMock,
) -> None:
    _assert_problem(client.get("/v1/github/owners/octocat?x=1"), 400, "invalid_request")
    _assert_problem(
        client.get("/v1/github/owners/octocat", headers={"Accept": "text/plain"}),
        406,
        "not_acceptable",
    )
    method = client.post("/v1/github/owners/octocat", content=b"must-not-be-read")
    _assert_problem(method, 405, "method_not_allowed")
    assert method.headers["Allow"] == "GET"
    mock_github_service.get_owner.assert_not_awaited()


@pytest.mark.parametrize(
    ("problem", "status", "code"),
    [
        (PortableProblem("github_not_found"), 404, "github_not_found"),
        (PortableProblem("github_upstream"), 502, "github_upstream"),
        (PortableProblem("github_timeout"), 504, "github_timeout"),
        (
            PortableProblem(
                "github_rate_limit",
                headers={"Retry-After": "60", "X-RateLimit-Reset": "9007199254740991"},
            ),
            429,
            "github_rate_limit",
        ),
    ],
)
def test_github_controlled_failures_keep_safe_mapping_and_headers(
    client: TestClient,
    mock_github_service: AsyncMock,
    problem: PortableProblem,
    status: int,
    code: str,
) -> None:
    mock_github_service.get_owner.side_effect = problem
    response = client.get("/v1/github/owners/octocat")
    _assert_problem(response, status, code)
    if status == 429:
        assert response.headers["Retry-After"] == "60"
        assert response.headers["X-RateLimit-Reset"] == "9007199254740991"
