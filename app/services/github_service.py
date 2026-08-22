"""Credential-free, bounded GitHub REST transport and public projection."""

import asyncio
import math
import re
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast
from urllib.parse import quote, urljoin, urlsplit

import httpx2
from pydantic import ValidationError

from app.core.content_negotiation import strip_http_ows
from app.core.portable_http import parse_query_string, parse_strict_json, valid_json_content_type
from app.core.problems import PortableProblem
from app.models.github import (
    GitHubActivity,
    GitHubActivityPage,
    GitHubLanguage,
    GitHubLanguages,
    GitHubOwner,
    GitHubRepository,
    GitHubRepositoryPage,
    GitHubRepositorySummary,
    GitHubTag,
    GitHubTagPage,
)
from app.models.types import SAFE_INTEGER_MAX
from app.pagination import InvalidCursorError, decode_cursor, encode_cursor

GITHUB_ORIGIN = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"
GITHUB_USER_AGENT = "fastapi-playground/0.1.0"
GITHUB_RESPONSE_LIMIT = 4_194_304
GITHUB_TIMEOUT_SECONDS = 10.0
_MAX_REDIRECTS = 3
_REDIRECTS = frozenset({301, 302, 303, 307, 308})
_CANONICAL_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_BAD_URI_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")
_LINK_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_PROVIDER_TIMESTAMP = re.compile(
    r"([0-9]{4})-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])T"
    r"([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])(?:\.([0-9]+))?Z\Z"
)
_NUMERIC = r"(?:0|[1-9][0-9]*)"
_TIMESTAMP_MILLISECOND_DIGITS = 3
_MIN_ACTIVITY_CURSOR_PAGE = 2
_MIN_QUOTED_VALUE_LENGTH = 2
_ASCII_CONTROL_LIMIT = 0x20
_ASCII_DELETE = 0x7F
_HTTP_OK = 200
_HTTP_NOT_FOUND = 404
_HTTP_QUOTA_STATUSES = frozenset({403, 429})


class GitHubUpstreamError(Exception):
    """Provider transport, protocol, or projection failure."""


class GitHubNotFoundError(Exception):
    """Provider returned 404."""


@dataclass(slots=True)
class GitHubRateLimitError(Exception):
    """Provider returned a primary or secondary quota response."""

    headers: dict[str, str]


@dataclass(frozen=True, slots=True)
class ProviderResult:
    data: object
    headers: httpx2.Headers


def _header_values(headers: httpx2.Headers, name: str) -> list[str]:
    target = name.lower().encode("ascii")
    return [value.decode("latin1") for key, value in headers.raw if key.lower() == target]


def _canonical_safe_integer(value: str) -> int | None:
    if _CANONICAL_DECIMAL.fullmatch(value) is None:
        return None
    maximum = str(SAFE_INTEGER_MAX)
    if len(value) > len(maximum) or (len(value) == len(maximum) and value > maximum):
        return None
    return int(value)


def _provider_content_length(value: str) -> int | None:
    if not value or not value.isascii() or not value.isdecimal():
        return None
    normalized = value.lstrip("0") or "0"
    if len(normalized) > len(str(GITHUB_RESPONSE_LIMIT)):
        return GITHUB_RESPONSE_LIMIT + 1
    return int(normalized)


def _strict_int(value: object) -> int:
    if type(value) is not int or not 0 <= value <= SAFE_INTEGER_MAX:
        raise GitHubUpstreamError
    return value


def _strict_string(value: object, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value):
        raise GitHubUpstreamError
    return value


def _strict_bool(value: object) -> bool:
    if type(value) is not bool:
        raise GitHubUpstreamError
    return value


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise GitHubUpstreamError
    return cast("dict[str, object]", value)


def _array(value: object) -> list[object]:
    if not isinstance(value, list):
        raise GitHubUpstreamError
    return cast("list[object]", value)


def _display(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None or value == "":
        return None
    return _strict_string(value)


def canonical_provider_timestamp(value: object) -> str:
    """Validate a whole-millisecond UTC provider instant and emit three digits."""
    text = _strict_string(value)
    match = _PROVIDER_TIMESTAMP.fullmatch(text)
    if match is None:
        raise GitHubUpstreamError
    year, month, day, hour, minute, second, fraction = match.groups()
    try:
        datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), tzinfo=UTC)
    except ValueError as error:
        raise GitHubUpstreamError from error
    fraction = fraction or ""
    if len(fraction) > _TIMESTAMP_MILLISECOND_DIGITS and any(
        character != "0" for character in fraction[_TIMESTAMP_MILLISECOND_DIGITS:]
    ):
        raise GitHubUpstreamError
    milliseconds = fraction[:_TIMESTAMP_MILLISECOND_DIGITS].ljust(_TIMESTAMP_MILLISECOND_DIGITS, "0")
    return f"{year}-{month}-{day}T{hour}:{minute}:{second}.{milliseconds}Z"


def scalar_sort_key(value: str) -> tuple[int, ...]:
    """Sort strings by Unicode scalar values without locale or normalization."""
    return tuple(ord(character) for character in value)


def _split_link_values(value: str) -> list[str]:
    parts: list[str] = []
    start = 0
    quoted = False
    escaped = False
    angled = False
    for index, character in enumerate(value):
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character == "<":
            angled = True
        elif character == ">":
            angled = False
        elif character == "," and not angled:
            parts.append(strip_http_ows(value[start:index]))
            start = index + 1
    parts.append(strip_http_ows(value[start:]))
    return [part for part in parts if part]


def _split_link_parameters(value: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quoted = False
    escaped = False
    angled = False
    for character in value:
        if escaped:
            current.append(character)
            escaped = False
        elif quoted and character == "\\":
            current.append(character)
            escaped = True
        elif character == '"':
            current.append(character)
            quoted = not quoted
        elif not quoted and character == "<":
            if angled:
                raise GitHubUpstreamError
            current.append(character)
            angled = True
        elif not quoted and character == ">":
            if not angled:
                raise GitHubUpstreamError
            current.append(character)
            angled = False
        elif character == ";" and not quoted and not angled:
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    if quoted or escaped or angled:
        raise GitHubUpstreamError
    parts.append("".join(current))
    return parts


def _link_parameter_name(parameter: str) -> str:
    name = strip_http_ows(parameter.partition("=")[0]).lower()
    return name if _LINK_TOKEN.fullmatch(name) else ""


def _decoded_quoted_string(value: str) -> str | None:
    if len(value) < _MIN_QUOTED_VALUE_LENGTH or not value.startswith('"') or not value.endswith('"'):
        return None
    result: list[str] = []
    escaped = False
    for character in value[1:-1]:
        if escaped:
            result.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif ord(character) < _ASCII_CONTROL_LIMIT or ord(character) == _ASCII_DELETE:
            return None
        else:
            result.append(character)
    return None if escaped else "".join(result)


def _parse_link_relations(headers: httpx2.Headers) -> dict[str, str]:  # noqa: C901, PLR0912
    relations: dict[str, str] = {}
    for field in _header_values(headers, "link"):
        for link_value in _split_link_values(field):
            try:
                parts = _split_link_parameters(link_value)
            except GitHubUpstreamError as error:
                if re.search(r"(?:^|;)\s*rel\s*=", link_value, re.IGNORECASE):
                    raise GitHubUpstreamError from error
                continue
            parameters = [strip_http_ows(parameter) for parameter in parts[1:]]
            parameters = [parameter for parameter in parameters if parameter]
            if any(_link_parameter_name(parameter) == "anchor" for parameter in parameters):
                continue
            relevant: list[str] = []
            seen_rel = False
            for parameter in parameters:
                if _link_parameter_name(parameter) != "rel" or seen_rel:
                    continue
                seen_rel = True
                _, equals, raw_value = parameter.partition("=")
                value = strip_http_ows(raw_value)
                if not equals:
                    raise GitHubUpstreamError
                decoded = value if _LINK_TOKEN.fullmatch(value) else _decoded_quoted_string(value)
                if not decoded:
                    raise GitHubUpstreamError
                if (
                    decoded.startswith(" ")
                    or decoded.endswith(" ")
                    or any(character.isspace() and character != " " for character in decoded)
                ):
                    raise GitHubUpstreamError
                relevant.extend(
                    relation
                    for relation in (part.lower() for part in decoded.split(" ") if part)
                    if relation in {"next", "prev"}
                )
            if not relevant:
                continue
            target_match = re.fullmatch(r"<([^>]*)>", strip_http_ows(parts[0]))
            if target_match is None or len(relevant) != len(set(relevant)):
                raise GitHubUpstreamError
            target = target_match.group(1)
            for relation in relevant:
                if relation in relations:
                    raise GitHubUpstreamError
                relations[relation] = target
    return relations


def _validate_uri_text(value: str) -> None:
    if (
        not value.isascii()
        or "\\" in value
        or _BAD_URI_PERCENT.search(value)
        or any(ord(character) <= _ASCII_CONTROL_LIMIT or ord(character) == _ASCII_DELETE for character in value)
    ):
        raise GitHubUpstreamError


def _origin_tuple(url: str) -> tuple[str, str, int | None]:
    _validate_uri_text(url)
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as error:
        raise GitHubUpstreamError from error
    if parsed.username is not None or parsed.password is not None:
        raise GitHubUpstreamError
    if port is None:
        port = 443 if parsed.scheme.lower() == "https" else 80 if parsed.scheme.lower() == "http" else None
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), port


def _matches_numeric_path(path: str, pattern: re.Pattern[str]) -> bool:
    if pattern.fullmatch(path) is None:
        return False
    numeric_segments = [segment for segment in path.split("/") if segment.isascii() and segment.isdecimal()]
    return len(numeric_segments) == 1 and _canonical_safe_integer(numeric_segments[0]) is not None


def _repository_path(owner: str, repo: str, suffix: str = "") -> str:
    if repo and all(character == "." for character in repo):
        raise PortableProblem(
            "validation_failed",
            errors=[{"detail": "Request field is invalid"}],
        )
    return f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}{suffix}"


def _safe_provider_query(url: str) -> dict[str, str]:
    parsed = urlsplit(url)
    if parsed.fragment or parsed.username or parsed.password:
        raise GitHubUpstreamError
    try:
        return parse_query_string(parsed.query.encode("ascii"))
    except (UnicodeEncodeError, PortableProblem) as error:
        raise GitHubUpstreamError from error


def _validate_target(
    target: str,
    *,
    base_url: str,
    named_path: str,
    numeric_pattern: re.Pattern[str],
    query: dict[str, str],
) -> str:
    if _origin_tuple(target) != _origin_tuple(base_url):
        raise GitHubUpstreamError
    parsed = urlsplit(target)
    if parsed.path != named_path and not _matches_numeric_path(parsed.path, numeric_pattern):
        raise GitHubUpstreamError
    if _safe_provider_query(target) != query:
        raise GitHubUpstreamError
    return target


def _quota_headers(headers: httpx2.Headers, now: float) -> dict[str, str]:
    def usable(name: str) -> int | None:
        values = _header_values(headers, name)
        if len(values) != 1 or "," in values[0]:
            return None
        return _canonical_safe_integer(values[0])

    retry_after = usable("retry-after")
    reset = usable("x-ratelimit-reset")
    result: dict[str, str] = {}
    if reset is not None and reset > now:
        result["X-RateLimit-Reset"] = str(reset)
    if retry_after is not None:
        result["Retry-After"] = str(retry_after)
    elif reset is not None and reset > now:
        result["Retry-After"] = str(max(1, math.ceil(reset - now)))
    else:
        result["Retry-After"] = "60"
    return result


class GitHubClient:
    """One-operation anonymous GitHub HTTP client with manual redirects and bounds."""

    def __init__(
        self,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
        base_url: str = GITHUB_ORIGIN,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.transport = transport
        self.now = now or time.time

    async def get_json(  # noqa: C901, PLR0912, PLR0915 - one bounded transport state machine
        self,
        path: str,
        query: dict[str, str],
        *,
        numeric_pattern: re.Pattern[str],
    ) -> ProviderResult:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": GITHUB_USER_AGENT,
            "Accept-Encoding": "identity",
        }
        url = f"{self.base_url}{path}"
        visited: set[str] = set()
        redirects = 0
        try:
            async with httpx2.AsyncClient(
                transport=self.transport,
                follow_redirects=False,
                timeout=None,
                trust_env=False,
            ) as client:
                client.headers.clear()
                while True:
                    request_url = httpx2.URL(url, params=query)
                    canonical_url = str(request_url)
                    if canonical_url in visited:
                        raise GitHubUpstreamError
                    visited.add(canonical_url)
                    async with client.stream("GET", request_url, headers=headers) as response:
                        encodings = _header_values(response.headers, "content-encoding")
                        if len(encodings) > 1 or (encodings and strip_http_ows(encodings[0]).lower() != "identity"):
                            raise GitHubUpstreamError
                        if response.status_code in _REDIRECTS:
                            if redirects >= _MAX_REDIRECTS:
                                raise GitHubUpstreamError
                            locations = _header_values(response.headers, "location")
                            if len(locations) != 1 or not locations[0]:
                                raise GitHubUpstreamError
                            _validate_uri_text(locations[0])
                            target = urljoin(canonical_url, locations[0])
                            url = _validate_target(
                                target,
                                base_url=self.base_url,
                                named_path=path,
                                numeric_pattern=numeric_pattern,
                                query=query,
                            ).split("?", maxsplit=1)[0]
                            redirects += 1
                            continue
                        if response.status_code == _HTTP_NOT_FOUND:
                            raise GitHubNotFoundError
                        if response.status_code in _HTTP_QUOTA_STATUSES:
                            raise GitHubRateLimitError(_quota_headers(response.headers, float(self.now())))
                        if response.status_code != _HTTP_OK:
                            raise GitHubUpstreamError
                        content_types = _header_values(response.headers, "content-type")
                        if len(content_types) != 1 or not valid_json_content_type(content_types[0]):
                            raise GitHubUpstreamError
                        lengths = _header_values(response.headers, "content-length")
                        if lengths:
                            raw_lengths = [strip_http_ows(part) for value in lengths for part in value.split(",")]
                            parsed_lengths = [_provider_content_length(value) for value in raw_lengths]
                            if (
                                not raw_lengths
                                or any(value is None for value in parsed_lengths)
                                or len(set(parsed_lengths)) != 1
                            ):
                                raise GitHubUpstreamError
                            if parsed_lengths[0] is not None and parsed_lengths[0] > GITHUB_RESPONSE_LIMIT:
                                raise GitHubUpstreamError
                        chunks: list[bytes] = []
                        size = 0
                        if response.is_stream_consumed:
                            chunks.append(response.content)
                            size = len(response.content)
                            if size > GITHUB_RESPONSE_LIMIT:
                                raise GitHubUpstreamError
                        else:
                            async for chunk in response.aiter_raw():
                                size += len(chunk)
                                if size > GITHUB_RESPONSE_LIMIT:
                                    raise GitHubUpstreamError
                                chunks.append(chunk)
                        try:
                            data = parse_strict_json(b"".join(chunks))
                        except PortableProblem as error:
                            raise GitHubUpstreamError from error
                        return ProviderResult(data=data, headers=response.headers)
        except GitHubUpstreamError, GitHubNotFoundError, GitHubRateLimitError:
            raise
        except httpx2.RequestError as error:
            raise GitHubUpstreamError from error


class GitHubService:
    """Validate provider data, translate pagination, and expose closed public models."""

    def __init__(self, client: GitHubClient | None = None) -> None:
        self.client = client or GitHubClient()

    async def _run[T](self, operation: Coroutine[Any, Any, T]) -> T:
        try:
            async with asyncio.timeout(GITHUB_TIMEOUT_SECONDS):
                return await operation
        except TimeoutError:
            raise PortableProblem("github_timeout") from None
        except GitHubNotFoundError:
            raise PortableProblem("github_not_found") from None
        except GitHubRateLimitError as error:
            raise PortableProblem("github_rate_limit", headers=error.headers) from None
        except GitHubUpstreamError:
            raise PortableProblem("github_upstream") from None

    async def get_owner(self, owner: str) -> GitHubOwner:
        return await self._run(self._get_owner(owner))

    async def _get_owner(self, owner: str) -> GitHubOwner:
        path = f"/users/{quote(owner, safe='')}"
        result = await self.client.get_json(path, {}, numeric_pattern=re.compile(rf"/user/{_NUMERIC}\Z"))
        data = _object(result.data)
        try:
            return GitHubOwner.model_validate(
                {
                    "id": _strict_int(data.get("id")),
                    "login": _strict_string(data.get("login")),
                    "type": _strict_string(data.get("type")),
                    "name": _display(data, "name"),
                    "avatarUrl": _strict_string(data.get("avatar_url")),
                    "htmlUrl": _strict_string(data.get("html_url")),
                    "company": _display(data, "company"),
                    "blog": _display(data, "blog"),
                    "location": _display(data, "location"),
                    "bio": _display(data, "bio"),
                    "publicRepos": _strict_int(data.get("public_repos")),
                    "followers": _strict_int(data.get("followers")),
                    "following": _strict_int(data.get("following")),
                    "createdAt": canonical_provider_timestamp(data.get("created_at")),
                    "updatedAt": canonical_provider_timestamp(data.get("updated_at")),
                },
                strict=True,
            )
        except ValidationError as error:
            raise GitHubUpstreamError from error

    @staticmethod
    def _repo_summary(value: object) -> GitHubRepositorySummary:
        data = _object(value)
        if data.get("private") is not False or data.get("visibility") != "public":
            raise GitHubUpstreamError
        try:
            return GitHubRepositorySummary.model_validate(
                {
                    "id": _strict_int(data.get("id")),
                    "name": _strict_string(data.get("name")),
                    "fullName": _strict_string(data.get("full_name")),
                    "description": _display(data, "description"),
                    "htmlUrl": _strict_string(data.get("html_url")),
                    "fork": _strict_bool(data.get("fork")),
                },
                strict=True,
            )
        except ValidationError as error:
            raise GitHubUpstreamError from error

    async def get_repository(self, owner: str, repo: str) -> GitHubRepository:
        return await self._run(self._get_repository(owner, repo))

    async def _get_repository(self, owner: str, repo: str) -> GitHubRepository:
        path = _repository_path(owner, repo)
        result = await self.client.get_json(path, {}, numeric_pattern=re.compile(rf"/repositories/{_NUMERIC}\Z"))
        data = _object(result.data)
        summary = self._repo_summary(data)
        topics_raw = data.get("topics", [])
        topics = [_strict_string(value, empty=True) for value in _array(topics_raw)]
        if len(topics) != len(set(topics)):
            raise GitHubUpstreamError
        license_data = data.get("license")
        license_value: str | None = None
        if license_data is not None:
            license_object = _object(license_data)
            spdx = license_object.get("spdx_id")
            if spdx not in (None, "", "NOASSERTION"):
                license_value = _strict_string(spdx)
        language = data.get("language")
        if language is not None and not isinstance(language, str):
            raise GitHubUpstreamError
        pushed = data.get("pushed_at")
        try:
            return GitHubRepository.model_validate(
                {
                    **summary.model_dump(by_alias=True),
                    "language": language,
                    "stargazersCount": _strict_int(data.get("stargazers_count")),
                    "forksCount": _strict_int(data.get("forks_count")),
                    "openIssuesCount": _strict_int(data.get("open_issues_count")),
                    "archived": _strict_bool(data.get("archived")),
                    "createdAt": canonical_provider_timestamp(data.get("created_at")),
                    "updatedAt": canonical_provider_timestamp(data.get("updated_at")),
                    "pushedAt": None if pushed is None else canonical_provider_timestamp(pushed),
                    "defaultBranch": _strict_string(data.get("default_branch")),
                    "license": license_value,
                    "topics": sorted(topics, key=scalar_sort_key),
                    "disabled": _strict_bool(data.get("disabled")),
                },
                strict=True,
            )
        except ValidationError as error:
            raise GitHubUpstreamError from error

    @staticmethod
    def _numbered_cursor(
        operation: str,
        direction: Literal["next", "prev"],
        owner: str,
        limit: int,
        page: int,
        repo: str | None = None,
    ) -> str:
        state: dict[str, object] = {
            "direction": direction,
            "limit": limit,
            "operation": operation,
            "owner": owner,
            "page": page,
            "version": 1,
        }
        if repo is not None:
            state["repo"] = repo
        return encode_cursor(state)

    @staticmethod
    def decode_numbered_cursor(
        cursor: str | None,
        *,
        operation: str,
        owner: str,
        limit: int,
        repo: str | None = None,
    ) -> int:
        if cursor is None:
            return 1
        state = decode_cursor(cursor)
        expected_keys = {"direction", "limit", "operation", "owner", "page", "version"}
        if repo is not None:
            expected_keys.add("repo")
        if set(state) != expected_keys:
            raise InvalidCursorError
        page = state.get("page")
        if (
            type(state.get("version")) is not int
            or state.get("version") != 1
            or state.get("operation") != operation
            or state.get("owner") != owner
            or state.get("repo") != repo
            or type(state.get("limit")) is not int
            or state.get("limit") != limit
            or state.get("direction") not in ("next", "prev")
            or type(page) is not int
            or not 1 <= page <= SAFE_INTEGER_MAX
            or (state.get("direction") == "next" and page == 1)
        ):
            raise InvalidCursorError
        return page

    @staticmethod
    def _numbered_links(
        headers: httpx2.Headers,
        *,
        base_url: str,
        path: str,
        numeric_pattern: re.Pattern[str],
        fixed_query: dict[str, str],
        current_page: int,
        item_count: int,
    ) -> dict[str, int]:
        links = _parse_link_relations(headers)
        result: dict[str, int] = {}
        for relation, target in links.items():
            if _origin_tuple(target) != _origin_tuple(base_url):
                raise GitHubUpstreamError
            parsed = urlsplit(target)
            if parsed.path != path and not _matches_numeric_path(parsed.path, numeric_pattern):
                raise GitHubUpstreamError
            query = _safe_provider_query(target)
            page_text = query.pop("page", None)
            if page_text is None or query != fixed_query:
                raise GitHubUpstreamError
            page = _canonical_safe_integer(page_text)
            if page is None or page < 1:
                raise GitHubUpstreamError
            if relation == "next" and (item_count == 0 or page <= current_page):
                raise GitHubUpstreamError
            if relation == "prev" and page >= current_page:
                raise GitHubUpstreamError
            result[relation] = page
        return result

    async def list_owner_repositories(
        self, owner: str, limit: int, cursor: str | None
    ) -> tuple[GitHubRepositoryPage, str | None, str | None]:
        return await self._run(self._list_owner_repositories(owner, limit, cursor))

    async def _list_owner_repositories(
        self, owner: str, limit: int, cursor: str | None
    ) -> tuple[GitHubRepositoryPage, str | None, str | None]:
        page = self.decode_numbered_cursor(cursor, operation="listGitHubOwnerRepositories", owner=owner, limit=limit)
        path = f"/users/{quote(owner, safe='')}/repos"
        fixed = {"type": "owner", "sort": "full_name", "direction": "asc", "per_page": str(limit)}
        query = {**fixed, **({"page": str(page)} if cursor is not None else {})}
        pattern = re.compile(rf"/user/{_NUMERIC}/repos\Z")
        result = await self.client.get_json(path, query, numeric_pattern=pattern)
        values = _array(result.data)
        if len(values) > limit:
            raise GitHubUpstreamError
        repos = [self._repo_summary(value) for value in values]
        links = self._numbered_links(
            result.headers,
            base_url=self.client.base_url,
            path=path,
            numeric_pattern=pattern,
            fixed_query=fixed,
            current_page=page,
            item_count=len(repos),
        )
        next_cursor = (
            self._numbered_cursor("listGitHubOwnerRepositories", "next", owner, limit, links["next"])
            if "next" in links
            else None
        )
        prev_cursor = None
        if "prev" in links:
            prev_cursor = (
                ""
                if links["prev"] == 1
                else self._numbered_cursor("listGitHubOwnerRepositories", "prev", owner, limit, links["prev"])
            )
        return GitHubRepositoryPage(repos=repos, count=len(repos)), next_cursor, prev_cursor

    @staticmethod
    def _activity_cursor(
        direction: Literal["next", "prev"], owner: str, repo: str, limit: int, page: int, value: str
    ) -> str:
        try:
            return encode_cursor(
                {
                    "direction": direction,
                    "limit": limit,
                    "operation": "listGitHubRepositoryActivity",
                    "owner": owner,
                    "page": page,
                    "repo": repo,
                    "value": value,
                    "version": 1,
                }
            )
        except InvalidCursorError as error:
            raise GitHubUpstreamError from error

    @staticmethod
    def decode_activity_cursor(
        cursor: str | None, *, owner: str, repo: str, limit: int
    ) -> tuple[int, str | None, str | None]:
        if cursor is None:
            return 1, None, None
        state = decode_cursor(cursor)
        if set(state) != {"direction", "limit", "operation", "owner", "page", "repo", "value", "version"}:
            raise InvalidCursorError
        direction = state.get("direction")
        page = state.get("page")
        value = state.get("value")
        if (
            type(state.get("version")) is not int
            or state.get("version") != 1
            or state.get("operation") != "listGitHubRepositoryActivity"
            or state.get("owner") != owner
            or state.get("repo") != repo
            or type(state.get("limit")) is not int
            or state.get("limit") != limit
            or direction not in ("next", "prev")
            or type(page) is not int
            or not _MIN_ACTIVITY_CURSOR_PAGE <= page <= SAFE_INTEGER_MAX
            or not isinstance(value, str)
            or re.fullmatch(r"[!-~]{1,2048}", value) is None
        ):
            raise InvalidCursorError
        return page, "after" if direction == "next" else "before", value

    async def list_repository_activity(
        self, owner: str, repo: str, limit: int, cursor: str | None
    ) -> tuple[GitHubActivityPage, str | None, str | None]:
        return await self._run(self._list_repository_activity(owner, repo, limit, cursor))

    async def _list_repository_activity(  # noqa: C901, PLR0912 - projection and link validation are one boundary
        self, owner: str, repo: str, limit: int, cursor: str | None
    ) -> tuple[GitHubActivityPage, str | None, str | None]:
        page, member, value = self.decode_activity_cursor(cursor, owner=owner, repo=repo, limit=limit)
        path = _repository_path(owner, repo, "/activity")
        fixed = {"direction": "desc", "per_page": str(limit)}
        query = {**fixed, **({member: value} if member is not None and value is not None else {})}
        pattern = re.compile(rf"/repositories/{_NUMERIC}/activity\Z")
        result = await self.client.get_json(path, query, numeric_pattern=pattern)
        values = _array(result.data)
        if len(values) > limit:
            raise GitHubUpstreamError
        activities: list[GitHubActivity] = []
        for raw in values:
            data = _object(raw)
            actor_data = data.get("actor")
            actor = None
            avatar = None
            if actor_data is not None:
                actor_object = _object(actor_data)
                actor = _strict_string(actor_object.get("login"))
                avatar = _strict_string(actor_object.get("avatar_url"))
            try:
                activities.append(
                    GitHubActivity.model_validate(
                        {
                            "id": _strict_int(data.get("id")),
                            "actor": actor,
                            "actorAvatarUrl": avatar,
                            "ref": _strict_string(data.get("ref")),
                            "timestamp": canonical_provider_timestamp(data.get("timestamp")),
                            "activityType": _strict_string(data.get("activity_type")),
                        },
                        strict=True,
                    )
                )
            except ValidationError as error:
                raise GitHubUpstreamError from error
        links = _parse_link_relations(result.headers)
        navigation: dict[str, str] = {}
        for relation, target in links.items():
            if _origin_tuple(target) != _origin_tuple(self.client.base_url):
                raise GitHubUpstreamError
            parsed = urlsplit(target)
            if parsed.path != path and not _matches_numeric_path(parsed.path, pattern):
                raise GitHubUpstreamError
            target_query = _safe_provider_query(target)
            before = target_query.pop("before", None)
            after = target_query.pop("after", None)
            if target_query != fixed or (before is None) == (after is None):
                raise GitHubUpstreamError
            if relation == "next" and (not activities or after is None):
                raise GitHubUpstreamError
            if relation == "prev" and (cursor is None or before is None):
                raise GitHubUpstreamError
            target_value = after if relation == "next" else before
            if target_value is None or re.fullmatch(r"[!-~]{1,2048}", target_value) is None:
                raise GitHubUpstreamError
            if member == ("after" if relation == "next" else "before") and value == target_value:
                raise GitHubUpstreamError
            navigation[relation] = target_value
        if "next" in navigation and page == SAFE_INTEGER_MAX:
            raise GitHubUpstreamError
        next_cursor = (
            self._activity_cursor("next", owner, repo, limit, page + 1, navigation["next"])
            if "next" in navigation
            else None
        )
        prev_cursor = None
        if "prev" in navigation:
            prev_cursor = (
                ""
                if page <= _MIN_ACTIVITY_CURSOR_PAGE
                else self._activity_cursor("prev", owner, repo, limit, page - 1, navigation["prev"])
            )
        return GitHubActivityPage(activities=activities, count=len(activities)), next_cursor, prev_cursor

    async def list_repository_languages(self, owner: str, repo: str) -> GitHubLanguages:
        return await self._run(self._list_repository_languages(owner, repo))

    async def _list_repository_languages(self, owner: str, repo: str) -> GitHubLanguages:
        path = _repository_path(owner, repo, "/languages")
        result = await self.client.get_json(
            path, {}, numeric_pattern=re.compile(rf"/repositories/{_NUMERIC}/languages\Z")
        )
        data = _object(result.data)
        languages = [
            GitHubLanguage(name=_strict_string(name), bytes=_strict_int(byte_count))
            for name, byte_count in data.items()
        ]
        languages.sort(key=lambda item: (-item.bytes, scalar_sort_key(item.name)))
        return GitHubLanguages(languages=languages)

    async def list_repository_tags(
        self, owner: str, repo: str, limit: int, cursor: str | None
    ) -> tuple[GitHubTagPage, str | None, str | None]:
        return await self._run(self._list_repository_tags(owner, repo, limit, cursor))

    async def _list_repository_tags(
        self, owner: str, repo: str, limit: int, cursor: str | None
    ) -> tuple[GitHubTagPage, str | None, str | None]:
        page = self.decode_numbered_cursor(
            cursor, operation="listGitHubRepositoryTags", owner=owner, repo=repo, limit=limit
        )
        path = _repository_path(owner, repo, "/tags")
        fixed = {"per_page": str(limit)}
        query = {**fixed, **({"page": str(page)} if cursor is not None else {})}
        pattern = re.compile(rf"/repositories/{_NUMERIC}/tags\Z")
        result = await self.client.get_json(path, query, numeric_pattern=pattern)
        values = _array(result.data)
        if len(values) > limit:
            raise GitHubUpstreamError
        tags: list[GitHubTag] = []
        for raw in values:
            data = _object(raw)
            commit = _object(data.get("commit"))
            try:
                tags.append(
                    GitHubTag.model_validate(
                        {
                            "name": _strict_string(data.get("name")),
                            "commit": {"sha": _strict_string(commit.get("sha"))},
                        },
                        strict=True,
                    )
                )
            except ValidationError as error:
                raise GitHubUpstreamError from error
        links = self._numbered_links(
            result.headers,
            base_url=self.client.base_url,
            path=path,
            numeric_pattern=pattern,
            fixed_query=fixed,
            current_page=page,
            item_count=len(tags),
        )
        next_cursor = (
            self._numbered_cursor("listGitHubRepositoryTags", "next", owner, limit, links["next"], repo)
            if "next" in links
            else None
        )
        prev_cursor = None
        if "prev" in links:
            prev_cursor = (
                ""
                if links["prev"] == 1
                else self._numbered_cursor("listGitHubRepositoryTags", "prev", owner, limit, links["prev"], repo)
            )
        return GitHubTagPage(tags=tags, count=len(tags)), next_cursor, prev_cursor
