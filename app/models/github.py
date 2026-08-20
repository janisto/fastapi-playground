"""Closed public GitHub projection models."""

import re
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, WithJsonSchema

from app.models.types import SafeInteger

_TIMESTAMP_BODY = (
    r"[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\.[0-9]{3}Z"
)
_TIMESTAMP = re.compile(rf"{_TIMESTAMP_BODY}\Z")
_ASCII_SPACE = 0x20
_ASCII_DELETE = 0x7F
_BAD_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")


def _http_url(value: str) -> str:
    if (
        not value.isascii()
        or "\\" in value
        or _BAD_PERCENT.search(value)
        or any(ord(character) <= _ASCII_SPACE or ord(character) == _ASCII_DELETE for character in value)
    ):
        raise ValueError("invalid HTTP URL")
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError as error:
        raise ValueError("invalid HTTP URL") from error
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("invalid HTTP URL")
    return value


def _timestamp(value: str) -> str:
    if _TIMESTAMP.fullmatch(value) is None:
        raise ValueError("invalid canonical timestamp")
    return value


HttpURL = Annotated[str, AfterValidator(_http_url), WithJsonSchema({"type": "string", "format": "uri"})]
CanonicalTimestamp = Annotated[
    str,
    AfterValidator(_timestamp),
    WithJsonSchema({"type": "string", "format": "date-time", "pattern": rf"^{_TIMESTAMP_BODY}$"}),
]


class GitHubModel(BaseModel):
    """Strict closed projection base."""

    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)


class GitHubOwner(GitHubModel):
    id: SafeInteger
    login: str = Field(min_length=1, strict=True)
    type: str = Field(min_length=1, strict=True)
    name: str | None
    avatar_url: HttpURL = Field(alias="avatarUrl")
    html_url: HttpURL = Field(alias="htmlUrl")
    company: str | None
    blog: str | None
    location: str | None
    bio: str | None
    public_repos: SafeInteger = Field(alias="publicRepos")
    followers: SafeInteger
    following: SafeInteger
    created_at: CanonicalTimestamp = Field(alias="createdAt")
    updated_at: CanonicalTimestamp = Field(alias="updatedAt")


class GitHubRepositorySummary(GitHubModel):
    id: SafeInteger
    name: str = Field(min_length=1, strict=True)
    full_name: str = Field(alias="fullName", min_length=1, strict=True)
    description: str | None
    html_url: HttpURL = Field(alias="htmlUrl")
    fork: bool = Field(strict=True)


class GitHubRepository(GitHubRepositorySummary):
    language: str | None
    stargazers_count: SafeInteger = Field(alias="stargazersCount")
    forks_count: SafeInteger = Field(alias="forksCount")
    open_issues_count: SafeInteger = Field(alias="openIssuesCount")
    archived: bool = Field(strict=True)
    created_at: CanonicalTimestamp = Field(alias="createdAt")
    updated_at: CanonicalTimestamp = Field(alias="updatedAt")
    pushed_at: CanonicalTimestamp | None = Field(alias="pushedAt")
    default_branch: str = Field(alias="defaultBranch", min_length=1, strict=True)
    license: str | None
    topics: list[str] = Field(json_schema_extra={"uniqueItems": True})
    disabled: bool = Field(strict=True)


class GitHubActivity(GitHubModel):
    id: SafeInteger
    actor: str | None
    actor_avatar_url: HttpURL | None = Field(alias="actorAvatarUrl")
    ref: str = Field(min_length=1, strict=True)
    timestamp: CanonicalTimestamp
    activity_type: str = Field(alias="activityType", min_length=1, strict=True)


class GitHubLanguage(GitHubModel):
    name: str = Field(min_length=1, strict=True)
    bytes: SafeInteger


class GitHubCommit(GitHubModel):
    sha: str = Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$", strict=True)


class GitHubTag(GitHubModel):
    name: str = Field(min_length=1, strict=True)
    commit: GitHubCommit


class GitHubRepositoryPage(GitHubModel):
    repos: list[GitHubRepositorySummary] = Field(max_length=100)
    count: int = Field(ge=0, le=100, strict=True)


class GitHubActivityPage(GitHubModel):
    activities: list[GitHubActivity] = Field(max_length=100)
    count: int = Field(ge=0, le=100, strict=True)


class GitHubLanguages(GitHubModel):
    languages: list[GitHubLanguage]


class GitHubTagPage(GitHubModel):
    tags: list[GitHubTag] = Field(max_length=100)
    count: int = Field(ge=0, le=100, strict=True)
