"""Deterministic adversarial GitHub transport, projection, pagination, and failure tests."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, override

import httpx2
import pytest

from app.core.problems import PortableProblem
from app.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.services.github_service import (
    GITHUB_RESPONSE_LIMIT,
    GITHUB_TIMEOUT_SECONDS,
    GITHUB_USER_AGENT,
    GitHubClient,
    GitHubService,
)


def _owner(**overrides: Any) -> dict[str, Any]:
    value = {
        "id": 1,
        "login": "octocat",
        "type": "User",
        "name": None,
        "avatar_url": "https://avatars.example/octocat",
        "html_url": "https://github.com/octocat",
        "company": "",
        "blog": None,
        "location": None,
        "bio": None,
        "public_repos": 8,
        "followers": 10,
        "following": 2,
        "created_at": "2011-01-25T18:44:36Z",
        "updated_at": "2026-01-01T00:00:00.1200Z",
        "email": "must-not-leak@example.test",
    }
    value.update(overrides)
    return value


def _repo(**overrides: Any) -> dict[str, Any]:
    value = {
        "id": 2,
        "name": "hello-world",
        "full_name": "octocat/hello-world",
        "description": None,
        "html_url": "https://github.com/octocat/hello-world",
        "fork": False,
        "private": False,
        "visibility": "public",
    }
    value.update(overrides)
    return value


def _repo_detail(**overrides: Any) -> dict[str, Any]:
    value = {
        **_repo(),
        "language": None,
        "stargazers_count": 3,
        "forks_count": 4,
        "open_issues_count": 5,
        "archived": False,
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2020-01-02T00:00:00.001Z",
        "pushed_at": None,
        "default_branch": "main",
        "license": {"spdx_id": "NOASSERTION"},
        "topics": ["\U00010000", "\ue000"],
        "disabled": False,
    }
    value.update(overrides)
    return value


def _service(
    handler: Callable[[httpx2.Request], httpx2.Response | Awaitable[httpx2.Response]],
    *,
    now: Callable[[], float] | None = None,
) -> GitHubService:
    async def async_handler(request: httpx2.Request) -> httpx2.Response:
        result = handler(request)
        if isinstance(result, httpx2.Response):
            return result
        return await result

    return GitHubService(
        GitHubClient(
            transport=httpx2.MockTransport(async_handler),
            base_url="https://api.github.test",
            now=now,
        )
    )


async def _invoke_repository_operation(
    service: GitHubService,
    operation: str,
    *,
    repo: str = "hello-world",
    limit: int = 20,
) -> object:
    if operation == "repository":
        return await service.get_repository("octocat", repo)
    if operation == "activity":
        return await service.list_repository_activity("octocat", repo, limit, None)
    if operation == "languages":
        return await service.list_repository_languages("octocat", repo)
    return await service.list_repository_tags("octocat", repo, limit, None)


async def test_owner_request_uses_fixed_anonymous_headers_and_closed_projection() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, headers={"Content-Type": "application/json; charset=utf-8"}, json=_owner())

    owner = await _service(handler).get_owner("octocat")
    assert owner.model_dump(by_alias=True) == {
        "id": 1,
        "login": "octocat",
        "type": "User",
        "name": None,
        "avatarUrl": "https://avatars.example/octocat",
        "htmlUrl": "https://github.com/octocat",
        "company": None,
        "blog": None,
        "location": None,
        "bio": None,
        "publicRepos": 8,
        "followers": 10,
        "following": 2,
        "createdAt": "2011-01-25T18:44:36.000Z",
        "updatedAt": "2026-01-01T00:00:00.120Z",
    }
    request = seen[0]
    assert request.url == "https://api.github.test/users/octocat"
    assert request.headers["Accept"] == "application/vnd.github+json"
    assert request.headers["X-GitHub-Api-Version"] == "2026-03-10"
    assert request.headers["User-Agent"] == GITHUB_USER_AGENT
    assert request.headers["Accept-Encoding"] == "identity"
    assert set(request.headers) == {
        "accept",
        "accept-encoding",
        "host",
        "user-agent",
        "x-github-api-version",
    }
    assert "authorization" not in request.headers
    assert GITHUB_TIMEOUT_SECONDS == 10.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", None),
        ("id", True),
        ("id", 9_007_199_254_740_992),
        ("login", ""),
        ("avatar_url", "javascript:alert(1)"),
        ("created_at", "2011-01-25T18:44:36.0001Z"),
    ],
)
async def test_owner_projection_fails_closed_on_missing_wrong_or_unsafe_values(field: str, value: object) -> None:
    payload = _owner()
    if value is None and field == "id":
        payload.pop(field)
    else:
        payload[field] = value
    service = _service(lambda _: httpx2.Response(200, headers={"Content-Type": "application/json"}, json=payload))
    with pytest.raises(PortableProblem, match="github_upstream"):
        await service.get_owner("octocat")


@pytest.mark.parametrize(
    "overrides",
    [
        {"private": True},
        {"visibility": "private"},
        {"topics": ["duplicate", "duplicate"]},
        {"stargazers_count": -1},
        {"updated_at": "2020-01-02T00:00:00.0001Z"},
        {"html_url": "javascript:alert(1)"},
        {"html_url": "https://éxample.test/repo"},
        {"html_url": "https://example.test/%ZZ"},
        {"html_url": "https://example.test\\attacker"},
    ],
)
async def test_repository_detail_fails_closed_on_private_or_invalid_projection(overrides: dict[str, Any]) -> None:
    service = _service(
        lambda _: httpx2.Response(200, headers={"Content-Type": "application/json"}, json=_repo_detail(**overrides))
    )
    with pytest.raises(PortableProblem) as captured:
        await service.get_repository("octocat", "hello-world")
    assert captured.value.code == "github_upstream"


async def test_repository_detail_sorts_topics_by_unicode_scalar_value_and_maps_nullable_fields() -> None:
    service = _service(
        lambda _: httpx2.Response(200, headers={"Content-Type": "application/json"}, json=_repo_detail())
    )
    repository = await service.get_repository("octocat", "hello-world")
    assert repository.topics == ["\ue000", "\U00010000"]
    assert repository.pushed_at is None
    assert repository.license is None
    assert "private" not in repository.model_dump(by_alias=True)


async def test_repository_page_reconstructs_fixed_query_and_translates_links() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert dict(request.url.params) == {
            "type": "owner",
            "sort": "full_name",
            "direction": "asc",
            "per_page": "1",
        }
        link = (
            "<https://api.github.test/users/octocat/repos"
            '?type=owner&sort=full_name&direction=asc&per_page=1&page=2>; rel="next"'
        )
        return httpx2.Response(200, headers=[("Content-Type", "application/json"), ("Link", link)], json=[_repo()])

    page, next_cursor, prev_cursor = await _service(handler).list_owner_repositories("octocat", 1, None)
    assert page.count == 1
    assert prev_cursor is None
    state = decode_cursor(next_cursor or "")
    assert state == {
        "direction": "next",
        "limit": 1,
        "operation": "listGitHubOwnerRepositories",
        "owner": "octocat",
        "page": 2,
        "version": 1,
    }


@pytest.mark.parametrize("operation", ["repositories", "tags"])
async def test_numbered_collections_cover_first_middle_terminal_and_later_empty_pages(operation: str) -> None:
    requests: list[dict[str, str]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        query = dict(request.url.params)
        requests.append(query)
        page = int(query.get("page", "1"))
        fixed = "type=owner&sort=full_name&direction=asc&per_page=1" if operation == "repositories" else "per_page=1"
        path = "users/octocat/repos" if operation == "repositories" else "repos/octocat/hello-world/tags"
        relations: list[str] = []
        if page < 3:
            relations.append(f'<https://api.github.test/{path}?{fixed}&page={page + 1}>; rel="next"')
        if page > 1:
            previous = 2 if page == 4 else page - 1
            relations.append(f'<https://api.github.test/{path}?{fixed}&page={previous}>; rel="prev"')
        headers = {"Content-Type": "application/json"}
        if relations:
            headers["Link"] = ", ".join(relations)
        if page == 4:
            payload: object = []
        elif operation == "repositories":
            payload = [_repo(id=page, name=f"repo-{page}", full_name=f"octocat/repo-{page}")]
        else:
            payload = [{"name": f"v{page}", "commit": {"sha": f"{page:x}" * 40}}]
        return httpx2.Response(200, headers=headers, json=payload)

    service = _service(handler)

    async def invoke(cursor: str | None) -> tuple[Any, str | None, str | None]:
        if operation == "repositories":
            return await service.list_owner_repositories("octocat", 1, cursor)
        return await service.list_repository_tags("octocat", "hello-world", 1, cursor)

    first, second_cursor, first_prev = await invoke(None)
    assert first.count == 1
    assert first_prev is None
    second, third_cursor, first_cursor = await invoke(second_cursor)
    assert second.count == 1
    assert first_cursor == ""
    terminal, no_next, second_again = await invoke(third_cursor)
    assert terminal.count == 1
    assert no_next is None
    assert decode_cursor(second_again or "")["page"] == 2

    state: dict[str, object] = {
        "direction": "next",
        "limit": 1,
        "operation": "listGitHubOwnerRepositories" if operation == "repositories" else "listGitHubRepositoryTags",
        "owner": "octocat",
        "page": 4,
        "version": 1,
    }
    if operation == "tags":
        state["repo"] = "hello-world"
    empty, empty_next, nonadjacent_prev = await invoke(encode_cursor(state))
    assert empty.count == 0
    assert empty_next is None
    assert decode_cursor(nonadjacent_prev or "")["page"] == 2
    assert [query.get("page", "1") for query in requests] == ["1", "2", "3", "4"]


@pytest.mark.parametrize(
    ("relation", "current_page", "target_page"),
    [("next", 1, 100), ("prev", 100, 2)],
)
async def test_numbered_provider_links_require_directional_progress_not_adjacency(
    relation: str,
    current_page: int,
    target_page: int,
) -> None:
    fixed = "type=owner&sort=full_name&direction=asc&per_page=1"
    target = f"https://api.github.test/users/octocat/repos?{fixed}&page={target_page}"
    requests: list[dict[str, str]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(dict(request.url.params))
        return httpx2.Response(
            200,
            headers={"Content-Type": "application/json", "Link": f'<{target}>; rel="{relation}"'},
            json=[_repo()],
        )

    cursor = None
    if current_page != 1:
        cursor = encode_cursor(
            {
                "direction": "next",
                "limit": 1,
                "operation": "listGitHubOwnerRepositories",
                "owner": "octocat",
                "page": current_page,
                "version": 1,
            }
        )
    _, next_cursor, prev_cursor = await _service(handler).list_owner_repositories("octocat", 1, cursor)

    navigation_cursor = next_cursor if relation == "next" else prev_cursor
    assert decode_cursor(navigation_cursor or "")["page"] == target_page
    assert requests == [
        {
            "type": "owner",
            "sort": "full_name",
            "direction": "asc",
            "per_page": "1",
            **({"page": str(current_page)} if cursor is not None else {}),
        }
    ]


async def test_numbered_cursor_scope_rejection_performs_no_fetch() -> None:
    calls = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(500)

    cursor = encode_cursor(
        {
            "direction": "next",
            "limit": 20,
            "operation": "listGitHubOwnerRepositories",
            "owner": "other",
            "page": 2,
            "version": 1,
        }
    )
    with pytest.raises(InvalidCursorError):
        await _service(handler).list_owner_repositories("octocat", 20, cursor)
    assert calls == 0


@pytest.mark.parametrize("field", ["version", "limit"])
async def test_boolean_numbered_cursor_integer_fields_are_rejected_without_fetch(field: str) -> None:
    calls = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(500)

    state: dict[str, object] = {
        "direction": "next",
        "limit": 1,
        "operation": "listGitHubOwnerRepositories",
        "owner": "octocat",
        "page": 2,
        "version": 1,
    }
    state[field] = True
    with pytest.raises(InvalidCursorError):
        await _service(handler).list_owner_repositories("octocat", 1, encode_cursor(state))
    assert calls == 0


async def test_activity_projects_deleted_actor_and_translates_after_link() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert dict(request.url.params) == {"direction": "desc", "per_page": "2"}
        link = (
            "<https://api.github.test/repos/octocat/hello-world/activity"
            '?direction=desc&per_page=2&after=cursor-2>; rel="next"'
        )
        payload = [
            {
                "id": 2,
                "actor": None,
                "ref": "refs/heads/main",
                "timestamp": "2026-01-02T00:00:00Z",
                "activity_type": "push",
            },
            {
                "id": 1,
                "actor": {"login": "octocat", "avatar_url": "https://avatars.example/o"},
                "ref": "refs/heads/main",
                "timestamp": "2026-01-01T00:00:00Z",
                "activity_type": "push",
            },
        ]
        return httpx2.Response(200, headers={"Content-Type": "application/json", "Link": link}, json=payload)

    page, next_cursor, prev_cursor = await _service(handler).list_repository_activity("octocat", "hello-world", 2, None)
    assert page.activities[0].actor is None
    assert page.activities[0].actor_avatar_url is None
    assert page.activities[1].actor == "octocat"
    assert prev_cursor is None
    assert decode_cursor(next_cursor or "")["value"] == "cursor-2"


async def test_activity_cursors_reconstruct_next_and_prev_and_cover_terminal_and_empty_pages() -> None:
    requests: list[dict[str, str]] = []
    activity_url = "https://api.github.test/repos/octocat/hello-world/activity"

    def activity(identifier: int) -> dict[str, object]:
        return {
            "id": identifier,
            "actor": None,
            "ref": "refs/heads/main",
            "timestamp": f"2026-01-0{identifier}T00:00:00Z",
            "activity_type": "push",
        }

    def handler(request: httpx2.Request) -> httpx2.Response:
        query = dict(request.url.params)
        requests.append(query)
        headers = {"Content-Type": "application/json"}
        payload: object
        if "before" in query:
            assert query == {"direction": "desc", "per_page": "1", "before": "p2"}
            payload = [activity(2)]
            headers["Link"] = (
                f'<{activity_url}?direction=desc&per_page=1&after=n3>; rel="next", '
                f'<{activity_url}?direction=desc&per_page=1&before=p1>; rel="prev"'
            )
        elif query.get("after") == "n4":
            payload = []
            headers["Link"] = f'<{activity_url}?direction=desc&per_page=1&before=p3>; rel="prev"'
        elif query.get("after") == "n3":
            payload = [activity(3)]
            headers["Link"] = f'<{activity_url}?direction=desc&per_page=1&before=p2>; rel="prev"'
        elif query.get("after") == "n2":
            payload = [activity(2)]
            headers["Link"] = (
                f'<{activity_url}?direction=desc&per_page=1&after=n3>; rel="next", '
                f'<{activity_url}?direction=desc&per_page=1&before=p1>; rel="prev"'
            )
        else:
            assert query == {"direction": "desc", "per_page": "1"}
            payload = [activity(1)]
            headers["Link"] = f'<{activity_url}?direction=desc&per_page=1&after=n2>; rel="next"'
        return httpx2.Response(200, headers=headers, json=payload)

    service = _service(handler)
    first, second_cursor, first_prev = await service.list_repository_activity("octocat", "hello-world", 1, None)
    assert first.count == 1
    assert first_prev is None
    middle, third_cursor, first_cursor = await service.list_repository_activity(
        "octocat", "hello-world", 1, second_cursor
    )
    assert middle.count == 1
    assert first_cursor == ""
    terminal, no_next, second_again = await service.list_repository_activity("octocat", "hello-world", 1, third_cursor)
    assert terminal.count == 1
    assert no_next is None
    assert decode_cursor(second_again or "")["value"] == "p2"
    back, _, _ = await service.list_repository_activity("octocat", "hello-world", 1, second_again)
    assert back.count == 1
    assert requests[-1] == {"direction": "desc", "per_page": "1", "before": "p2"}

    empty_cursor = GitHubService._activity_cursor("next", "octocat", "hello-world", 1, 4, "n4")
    empty, empty_next, previous = await service.list_repository_activity("octocat", "hello-world", 1, empty_cursor)
    assert empty.count == 0
    assert empty_next is None
    assert decode_cursor(previous or "")["value"] == "p3"


@pytest.mark.parametrize("relation", ["next", "prev"])
async def test_unencodable_activity_provider_navigation_is_upstream_failure(relation: str) -> None:
    activity_url = "https://api.github.test/repos/octocat/hello-world/activity"
    target_member = "after" if relation == "next" else "before"
    provider_value = "x" * 2048
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        expected_query = {"direction": "desc", "per_page": "1"}
        if relation == "prev":
            expected_query["after"] = "current"
        assert dict(request.url.params) == expected_query
        link = f'<{activity_url}?direction=desc&per_page=1&{target_member}={provider_value}>; rel="{relation}"'
        payload = [
            {
                "id": 1,
                "actor": None,
                "ref": "refs/heads/main",
                "timestamp": "2026-01-01T00:00:00Z",
                "activity_type": "push",
            }
        ]
        return httpx2.Response(200, headers={"Content-Type": "application/json", "Link": link}, json=payload)

    cursor = None
    if relation == "prev":
        cursor = GitHubService._activity_cursor("next", "octocat", "hello-world", 1, 3, "current")

    with pytest.raises(PortableProblem) as captured:
        await _service(handler).list_repository_activity("octocat", "hello-world", 1, cursor)
    assert captured.value.code == "github_upstream"
    assert calls == 1


async def test_languages_sort_by_bytes_then_unicode_scalars() -> None:
    payload = {"\U00010000": 5, "Z": 10, "\ue000": 5}
    service = _service(lambda _: httpx2.Response(200, headers={"Content-Type": "application/json"}, json=payload))
    result = await service.list_repository_languages("octocat", "hello-world")
    assert [(item.name, item.bytes) for item in result.languages] == [("Z", 10), ("\ue000", 5), ("\U00010000", 5)]


async def test_tag_projection_accepts_40_and_64_character_lowercase_hashes() -> None:
    payload = [
        {"name": "v1", "commit": {"sha": "a" * 40}},
        {"name": "v2", "commit": {"sha": "b" * 64}},
    ]
    service = _service(lambda _: httpx2.Response(200, headers={"Content-Type": "application/json"}, json=payload))
    page, next_cursor, prev_cursor = await service.list_repository_tags("octocat", "hello-world", 2, None)
    assert [tag.commit.sha for tag in page.tags] == ["a" * 40, "b" * 64]
    assert next_cursor is prev_cursor is None


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (404, "github_not_found"),
        (403, "github_rate_limit"),
        (429, "github_rate_limit"),
        (401, "github_upstream"),
        (410, "github_upstream"),
        (422, "github_upstream"),
        (500, "github_upstream"),
        (201, "github_upstream"),
        (204, "github_upstream"),
    ],
)
async def test_provider_status_mapping_does_not_parse_error_bodies(status: int, expected: str) -> None:
    service = _service(
        lambda _: httpx2.Response(
            status,
            headers={"Content-Type": "text/plain", "X-RateLimit-Reset": "9999999999"},
            content=b"SECRET PROVIDER ERROR",
        ),
        now=lambda: 1,
    )
    with pytest.raises(PortableProblem) as captured:
        await service.get_owner("octocat")
    assert captured.value.code == expected
    if status in {403, 429}:
        assert captured.value.headers == {"X-RateLimit-Reset": "9999999999", "Retry-After": "9999999998"}
    else:
        assert captured.value.headers == {}


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"Retry-After": "7", "X-RateLimit-Reset": "bad"}, {"Retry-After": "7"}),
        ({"Retry-After": "01", "X-RateLimit-Reset": "102"}, {"Retry-After": "2", "X-RateLimit-Reset": "102"}),
        ({"Retry-After": "bad", "X-RateLimit-Reset": "100"}, {"Retry-After": "60"}),
    ],
)
async def test_quota_hints_are_independently_canonicalized(headers: dict[str, str], expected: dict[str, str]) -> None:
    service = _service(lambda _: httpx2.Response(403, headers=headers), now=lambda: 100.25)
    with pytest.raises(PortableProblem) as captured:
        await service.get_owner("octocat")
    assert captured.value.headers == expected


async def test_named_to_numeric_redirect_is_followed_once_without_body_parsing() -> None:
    urls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        urls.append(str(request.url))
        if len(urls) == 1:
            return httpx2.Response(
                301, headers={"Location": "/user/1", "Content-Encoding": "identity"}, content=b"ignored"
            )
        return httpx2.Response(200, headers={"Content-Type": "application/json"}, json=_owner())

    result = await _service(handler).get_owner("octocat")
    assert result.login == "octocat"
    assert urls == ["https://api.github.test/users/octocat", "https://api.github.test/user/1"]


@pytest.mark.parametrize(
    "location",
    [
        "https://evil.example/user/1",
        "/repos/octocat/private",
        "/user/01",
        "/user/1?extra=1",
        "/us\ter/1",
        "#fragment",
    ],
)
async def test_unsafe_redirects_fail_closed(location: str) -> None:
    service = _service(lambda _: httpx2.Response(302, headers={"Location": location}))
    with pytest.raises(PortableProblem) as captured:
        await service.get_owner("octocat")
    assert captured.value.code == "github_upstream"


@pytest.mark.parametrize(
    "headers",
    [
        {"Content-Type": "text/plain"},
        {"Content-Type": "application/json", "Content-Encoding": "gzip"},
        {"Content-Type": 'application/json; profile="a"b"'},
        {"Content-Type": "application/json; profile=a; profile=b"},
        {"Content-Type": "application/json; charset =utf-8"},
        {"Content-Type": "application/json; charset= utf-8"},
        {},
    ],
)
async def test_success_requires_json_media_and_identity_encoding(headers: dict[str, str]) -> None:
    service = _service(lambda _: httpx2.Response(200, headers=headers, content=json.dumps(_owner()).encode()))
    with pytest.raises(PortableProblem) as captured:
        await service.get_owner("octocat")
    assert captured.value.code == "github_upstream"


async def test_exact_four_mibibyte_body_is_allowed_and_next_byte_is_rejected() -> None:
    base = json.dumps(_owner(), separators=(",", ":")).encode()
    exact = base + b" " * (GITHUB_RESPONSE_LIMIT - len(base))
    result = await _service(
        lambda _: httpx2.Response(200, headers={"Content-Type": "application/json"}, content=exact)
    ).get_owner("octocat")
    assert result.id == 1

    oversized = exact + b" "
    with pytest.raises(PortableProblem) as captured:
        await _service(
            lambda _: httpx2.Response(200, headers={"Content-Type": "application/json"}, content=oversized)
        ).get_owner("octocat")
    assert captured.value.code == "github_upstream"


async def test_over_limit_provider_page_is_rejected_not_truncated() -> None:
    payload = [_repo(id=1), _repo(id=2)]
    service = _service(lambda _: httpx2.Response(200, headers={"Content-Type": "application/json"}, json=payload))
    with pytest.raises(PortableProblem) as captured:
        await service.list_owner_repositories("octocat", 1, None)
    assert captured.value.code == "github_upstream"


async def test_cross_origin_or_nonadvancing_provider_link_is_502() -> None:
    for target in (
        "https://evil.example/users/octocat/repos?type=owner&sort=full_name&direction=asc&per_page=1&page=2",
        "https://api.github.test/users/octocat/repos?type=owner&sort=full_name&direction=asc&per_page=1&page=1",
        "https://api.github.test/us\ters/octocat/repos?type=owner&sort=full_name&direction=asc&per_page=1&page=2",
    ):
        service = _service(
            lambda _, target=target: httpx2.Response(
                200,
                headers={"Content-Type": "application/json", "Link": f'<{target}>; rel="next"'},
                json=[_repo()],
            )
        )
        with pytest.raises(PortableProblem) as captured:
            await service.list_owner_repositories("octocat", 1, None)
        assert captured.value.code == "github_upstream"


async def test_deadline_maps_to_504_and_cancellation_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = asyncio.Event()

    async def handler(_: httpx2.Request) -> httpx2.Response:
        await gate.wait()
        return httpx2.Response(200, headers={"Content-Type": "application/json"}, json=_owner())

    monkeypatch.setattr("app.services.github_service.GITHUB_TIMEOUT_SECONDS", 0.01)
    service = _service(handler)
    with pytest.raises(PortableProblem) as captured:
        await service.get_owner("octocat")
    assert captured.value.code == "github_timeout"

    monkeypatch.setattr("app.services.github_service.GITHUB_TIMEOUT_SECONDS", 10.0)
    task = asyncio.create_task(service.get_owner("octocat"))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_redirects_share_one_overall_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.06)
        if calls == 1:
            return httpx2.Response(302, headers={"Location": "/user/1"})
        return httpx2.Response(200, headers={"Content-Type": "application/json"}, json=_owner())

    monkeypatch.setattr("app.services.github_service.GITHUB_TIMEOUT_SECONDS", 0.1)
    with pytest.raises(PortableProblem) as captured:
        await _service(handler).get_owner("octocat")
    assert captured.value.code == "github_timeout"
    assert calls == 2


class TrackingStream(httpx2.AsyncByteStream):
    def __init__(self, chunks: list[bytes], *, explode: bool = False) -> None:
        self.chunks = chunks
        self.explode = explode
        self.reads = 0

    @override
    async def __aiter__(self) -> AsyncIterator[bytes]:
        if self.explode:
            raise AssertionError("provider error body was consumed")
        for chunk in self.chunks:
            self.reads += 1
            yield chunk


async def test_streamed_body_bound_handles_missing_truthful_and_dishonest_lengths() -> None:
    base = json.dumps(_owner(), separators=(",", ":")).encode()
    exact = base + b" " * (GITHUB_RESPONSE_LIMIT - len(base))
    exact_stream = TrackingStream([exact[:1_000_000], exact[1_000_000:]])
    exact_service = _service(
        lambda _: httpx2.Response(
            200,
            headers={"Content-Type": 'application/vnd.github+json; profile="a;b,c"'},
            stream=exact_stream,
        )
    )
    assert (await exact_service.get_owner("octocat")).id == 1
    assert exact_stream.reads == 2

    dishonest_stream = TrackingStream([exact, b" "])
    dishonest_service = _service(
        lambda _: httpx2.Response(
            200,
            headers={"Content-Type": "application/json", "Content-Length": str(GITHUB_RESPONSE_LIMIT)},
            stream=dishonest_stream,
        )
    )
    with pytest.raises(PortableProblem, match="github_upstream"):
        await dishonest_service.get_owner("octocat")
    assert dishonest_stream.reads == 2

    early_stream = TrackingStream([exact + b" "])
    early_service = _service(
        lambda _: httpx2.Response(
            200,
            headers={"Content-Type": "application/json", "Content-Length": str(GITHUB_RESPONSE_LIMIT + 1)},
            stream=early_stream,
        )
    )
    with pytest.raises(PortableProblem, match="github_upstream"):
        await early_service.get_owner("octocat")
    assert early_stream.reads == 0


@pytest.mark.parametrize(("status", "expected"), [(404, "github_not_found"), (403, "github_rate_limit")])
async def test_error_statuses_never_consume_provider_body(status: int, expected: str) -> None:
    stream = TrackingStream([], explode=True)
    service = _service(lambda _: httpx2.Response(status, stream=stream))
    with pytest.raises(PortableProblem) as captured:
        await service.get_owner("octocat")
    assert captured.value.code == expected
    assert stream.reads == 0


async def test_content_encoding_is_rejected_before_not_found_mapping() -> None:
    service = _service(
        lambda _: httpx2.Response(
            404,
            headers={"Content-Encoding": "gzip"},
            stream=TrackingStream([], explode=True),
        )
    )
    with pytest.raises(PortableProblem) as captured:
        await service.get_owner("octocat")
    assert captured.value.code == "github_upstream"


@pytest.mark.parametrize(
    ("operation", "location", "payload"),
    [
        ("owner", "/user/1", _owner()),
        (
            "repos",
            "/user/1/repos?type=owner&sort=full_name&direction=asc&per_page=20",
            [_repo()],
        ),
        ("repository", "/repositories/2", _repo_detail()),
        ("activity", "/repositories/2/activity?direction=desc&per_page=20", []),
        ("languages", "/repositories/2/languages", {}),
        ("tags", "/repositories/2/tags?per_page=20", []),
    ],
)
async def test_each_named_to_numeric_redirect_pattern_succeeds(
    operation: str,
    location: str,
    payload: object,
) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx2.Response(302, headers={"Location": location})
        return httpx2.Response(200, headers={"Content-Type": "application/json"}, json=payload)

    service = _service(handler)
    if operation == "owner":
        await service.get_owner("octocat")
    elif operation == "repos":
        await service.list_owner_repositories("octocat", 20, None)
    elif operation == "repository":
        await service.get_repository("octocat", "hello-world")
    elif operation == "activity":
        await service.list_repository_activity("octocat", "hello-world", 20, None)
    elif operation == "languages":
        await service.list_repository_languages("octocat", "hello-world")
    else:
        await service.list_repository_tags("octocat", "hello-world", 20, None)
    assert len(requests) == 2
    assert str(requests[1].url).removeprefix("https://api.github.test") == location


async def test_redirect_loop_and_fourth_redirect_fail_without_retry() -> None:
    loop_calls = 0

    def loop_handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal loop_calls
        loop_calls += 1
        return httpx2.Response(301, headers={"Location": "/users/octocat"})

    with pytest.raises(PortableProblem, match="github_upstream"):
        await _service(loop_handler).get_owner("octocat")
    assert loop_calls == 1

    redirect_calls = 0

    def redirect_handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal redirect_calls
        redirect_calls += 1
        return httpx2.Response(302, headers={"Location": f"/user/{redirect_calls}"})

    with pytest.raises(PortableProblem, match="github_upstream"):
        await _service(redirect_handler).get_owner("octocat")
    assert redirect_calls == 4


async def test_provider_link_parser_handles_multiple_fields_quoted_delimiters_and_anchor() -> None:
    next_target = (
        "https://api.github.test/users/octocat/repos?type=owner&sort=full_name&direction=asc&per_page=1&page=2"
    )
    ignored_target = next_target.replace("page=2", "page=99")
    headers = [
        ("Content-Type", "application/json"),
        ("Link", f'<{ignored_target}>; rel="last"; title="last, page"'),
        ("Link", f'<{next_target}>; title="next; page"; rel="next"'),
        ("Link", f'<{ignored_target}>; anchor="/other"; rel="prev"'),
    ]
    service = _service(lambda _: httpx2.Response(200, headers=headers, json=[_repo()]))
    _, next_cursor, prev_cursor = await service.list_owner_repositories("octocat", 1, None)
    assert decode_cursor(next_cursor or "")["page"] == 2
    assert prev_cursor is None


@pytest.mark.parametrize(
    "link",
    [
        '<https://api.github.test/users/octocat/repos?page=2>; rel="next',
        "<https://api.github.test/users/octocat/repos?page=2>; rel=",
        '<https://api.github.test/users/octocat/repos?page=2>; rel="next next"',
        'https://api.github.test/users/octocat/repos?page=2; rel="next"',
    ],
)
async def test_malformed_relevant_provider_link_is_502(link: str) -> None:
    service = _service(
        lambda _: httpx2.Response(
            200,
            headers={"Content-Type": "application/json", "Link": link},
            json=[_repo()],
        )
    )
    with pytest.raises(PortableProblem, match="github_upstream"):
        await service.list_owner_repositories("octocat", 1, None)


@pytest.mark.parametrize(
    "links",
    [
        [
            (
                "<https://api.github.test/users/octocat/repos"
                '?type=owner&sort=full_name&direction=asc&per_page=1&page=2>; rel="next"'
            ),
            (
                "<https://api.github.test/user/1/repos"
                '?type=owner&sort=full_name&direction=asc&per_page=1&page=3>; rel="next"'
            ),
        ],
        [
            (
                "<https://api.github.test/users/octocat/repos"
                '?type=owner&sort=full_name&direction=asc&per_page=1>; rel="next"'
            )
        ],
        [
            (
                "<https://api.github.test/user/9007199254740992/repos"
                '?type=owner&sort=full_name&direction=asc&per_page=1&page=2>; rel="next"'
            )
        ],
    ],
)
async def test_duplicate_missing_page_and_unsafe_numeric_provider_links_fail(links: list[str]) -> None:
    headers = [("Content-Type", "application/json"), *[("Link", link) for link in links]]
    service = _service(lambda _: httpx2.Response(200, headers=headers, json=[_repo()]))
    with pytest.raises(PortableProblem, match="github_upstream"):
        await service.list_owner_repositories("octocat", 1, None)


async def test_maximum_safe_numeric_provider_link_is_accepted() -> None:
    target = (
        "https://api.github.test/user/9007199254740991/repos?type=owner&sort=full_name&direction=asc&per_page=1&page=2"
    )
    service = _service(
        lambda _: httpx2.Response(
            200,
            headers={"Content-Type": "application/json", "Link": f'<{target}>; rel="next"'},
            json=[_repo()],
        )
    )
    _, next_cursor, _ = await service.list_owner_repositories("octocat", 1, None)
    assert decode_cursor(next_cursor or "")["page"] == 2


@pytest.mark.parametrize("operation", ["repository", "activity", "languages", "tags"])
async def test_service_repeats_dot_only_repo_guard_before_url_construction(operation: str) -> None:
    calls = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(500)

    service = _service(handler)
    with pytest.raises(PortableProblem) as captured:
        await _invoke_repository_operation(service, operation, repo="...")
    assert captured.value.code == "validation_failed"
    assert captured.value.errors == [{"detail": "Request field is invalid"}]
    assert calls == 0


@pytest.mark.parametrize(
    "mutation",
    [
        {"direction": "sideways"},
        {"limit": 21},
        {"owner": "other"},
        {"repo": "other"},
        {"page": 9_007_199_254_740_992},
        {"operation": "listGitHubRepositoryTags"},
    ],
)
async def test_activity_cursor_scope_rejection_never_fetches(mutation: dict[str, object]) -> None:
    calls = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(500)

    state: dict[str, object] = {
        "direction": "next",
        "limit": 20,
        "operation": "listGitHubRepositoryActivity",
        "owner": "octocat",
        "page": 2,
        "repo": "hello-world",
        "value": "after-value",
        "version": 1,
    }
    cursor = encode_cursor({**state, **mutation})
    with pytest.raises(InvalidCursorError):
        await _service(handler).list_repository_activity("octocat", "hello-world", 20, cursor)
    assert calls == 0


@pytest.mark.parametrize("field", ["version", "limit"])
async def test_boolean_activity_cursor_integer_fields_are_rejected_without_fetch(field: str) -> None:
    calls = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(500)

    state: dict[str, object] = {
        "direction": "next",
        "limit": 1,
        "operation": "listGitHubRepositoryActivity",
        "owner": "octocat",
        "page": 2,
        "repo": "hello-world",
        "value": "after-value",
        "version": 1,
    }
    state[field] = True
    with pytest.raises(InvalidCursorError):
        await _service(handler).list_repository_activity("octocat", "hello-world", 1, encode_cursor(state))
    assert calls == 0


async def test_activity_navigation_cannot_emit_a_page_beyond_safe_integer() -> None:
    state = {
        "direction": "next",
        "limit": 1,
        "operation": "listGitHubRepositoryActivity",
        "owner": "octocat",
        "page": 9_007_199_254_740_991,
        "repo": "hello-world",
        "value": "current",
        "version": 1,
    }
    link = (
        '<https://api.github.test/repos/octocat/hello-world/activity?direction=desc&per_page=1&after=next>; rel="next"'
    )
    service = _service(
        lambda _: httpx2.Response(
            200,
            headers={"Content-Type": "application/json", "Link": link},
            json=[
                {
                    "id": 1,
                    "actor": None,
                    "ref": "refs/heads/main",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "activity_type": "push",
                }
            ],
        )
    )
    with pytest.raises(PortableProblem, match="github_upstream"):
        await service.list_repository_activity("octocat", "hello-world", 1, encode_cursor(state))


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ([("Retry-After", "0")], {"Retry-After": "0"}),
        (
            [("Retry-After", "7"), ("X-RateLimit-Reset", "9007199254740991")],
            {"Retry-After": "7", "X-RateLimit-Reset": "9007199254740991"},
        ),
        ([("Retry-After", "1"), ("Retry-After", "2")], {"Retry-After": "60"}),
        ([("Retry-After", "1, 2")], {"Retry-After": "60"}),
        ([("X-RateLimit-Reset", "100")], {"Retry-After": "60"}),
        ([("X-RateLimit-Reset", "9007199254740992")], {"Retry-After": "60"}),
        ([("Retry-After", "9" * 5000)], {"Retry-After": "60"}),
    ],
)
async def test_quota_header_boundaries_and_ambiguity(
    headers: list[tuple[str, str]],
    expected: dict[str, str],
) -> None:
    calls = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(429, headers=headers)

    with pytest.raises(PortableProblem) as captured:
        await _service(handler, now=lambda: 100.0).get_owner("octocat")
    assert captured.value.code == "github_rate_limit"
    assert captured.value.headers == expected
    assert calls == 1


@pytest.mark.parametrize(
    ("payload", "operation"),
    [
        (
            [
                {
                    "id": 1,
                    "actor": {"login": "octocat"},
                    "ref": "refs/heads/main",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "activity_type": "push",
                }
            ],
            "activity",
        ),
        ([{"name": "v1", "commit": {"sha": "A" * 40}}], "tags"),
        ({"Python": -1}, "languages"),
    ],
)
async def test_invalid_activity_tag_and_language_projection_is_502(payload: object, operation: str) -> None:
    service = _service(lambda _: httpx2.Response(200, headers={"Content-Type": "application/json"}, json=payload))
    with pytest.raises(PortableProblem, match="github_upstream"):
        await _invoke_repository_operation(service, operation)


@pytest.mark.parametrize("operation", ["activity", "tags"])
async def test_every_paginated_projection_rejects_provider_page_over_limit(operation: str) -> None:
    payload: object
    if operation == "activity":
        activity = {
            "id": 1,
            "actor": None,
            "ref": "refs/heads/main",
            "timestamp": "2026-01-01T00:00:00Z",
            "activity_type": "push",
        }
        payload = [activity, {**activity, "id": 2}]
    else:
        payload = [
            {"name": "v1", "commit": {"sha": "a" * 40}},
            {"name": "v2", "commit": {"sha": "b" * 40}},
        ]
    service = _service(lambda _: httpx2.Response(200, headers={"Content-Type": "application/json"}, json=payload))
    with pytest.raises(PortableProblem, match="github_upstream"):
        await _invoke_repository_operation(service, operation, limit=1)


async def test_duplicate_provider_json_member_is_502() -> None:
    service = _service(
        lambda _: httpx2.Response(
            200,
            headers={"Content-Type": "application/json"},
            content=b'{"id":1,"id":2}',
        )
    )
    with pytest.raises(PortableProblem, match="github_upstream"):
        await service.get_owner("octocat")


async def test_ambient_github_token_is_not_read_or_attached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ambient-secret")
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, headers={"Content-Type": "application/json"}, json=_owner())

    await _service(handler).get_owner("octocat")
    assert len(requests) == 1
    assert "authorization" not in requests[0].headers
    assert "cookie" not in requests[0].headers
    assert "x-request-id" not in requests[0].headers
