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
        or parsed.query
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
    id: SafeInteger = Field(description="GitHub account identifier.", examples=[583231])
    login: str = Field(
        min_length=1,
        strict=True,
        description="Canonical GitHub account login.",
        examples=["octocat"],
    )
    type: str = Field(
        min_length=1,
        strict=True,
        description="Provider account type; values are intentionally open.",
        examples=["User"],
    )
    name: str | None = Field(description="Public display name, when present.", examples=["The Octocat"])
    avatar_url: HttpURL = Field(
        alias="avatarUrl",
        description="Absolute HTTP(S) avatar URL.",
        examples=["https://avatars.example.test/u/583231"],
    )
    html_url: HttpURL = Field(
        alias="htmlUrl",
        description="Absolute HTTP(S) public account page URL.",
        examples=["https://example.test/octocat"],
    )
    company: str | None = Field(description="Public company text, when present.", examples=["Example Corp"])
    blog: str | None = Field(
        description="Public blog text, when present; it is not assumed to be a URI.",
        examples=["octocat.example"],
    )
    location: str | None = Field(description="Public location text, when present.", examples=["Helsinki"])
    bio: str | None = Field(description="Public biography text, when present.", examples=["Builds portable APIs."])
    public_repos: SafeInteger = Field(
        alias="publicRepos",
        description="Number of public repositories.",
        examples=[8],
    )
    followers: SafeInteger = Field(description="Number of followers.", examples=[100])
    following: SafeInteger = Field(description="Number of followed accounts.", examples=[9])
    created_at: CanonicalTimestamp = Field(
        alias="createdAt",
        description="Account creation time in canonical UTC millisecond form.",
        examples=["2026-01-15T10:30:00.000Z"],
    )
    updated_at: CanonicalTimestamp = Field(
        alias="updatedAt",
        description="Account update time in canonical UTC millisecond form.",
        examples=["2026-01-16T11:45:00.000Z"],
    )


class GitHubRepositorySummary(GitHubModel):
    id: SafeInteger = Field(description="GitHub repository identifier.", examples=[1296269])
    name: str = Field(
        min_length=1,
        strict=True,
        description="Repository name.",
        examples=["portable-api"],
    )
    full_name: str = Field(
        alias="fullName",
        min_length=1,
        strict=True,
        description="Owner-qualified repository name.",
        examples=["octocat/portable-api"],
    )
    description: str | None = Field(
        description="Public repository description, when present.",
        examples=["A portable API example."],
    )
    html_url: HttpURL = Field(
        alias="htmlUrl",
        description="Absolute HTTP(S) public repository page URL.",
        examples=["https://example.test/octocat/portable-api"],
    )
    fork: bool = Field(strict=True, description="Whether the repository is a fork.", examples=[False])


class GitHubRepository(GitHubRepositorySummary):
    language: str | None = Field(description="Primary repository language, when present.", examples=["Python"])
    stargazers_count: SafeInteger = Field(
        alias="stargazersCount",
        description="Number of repository stars.",
        examples=[42],
    )
    forks_count: SafeInteger = Field(alias="forksCount", description="Number of repository forks.", examples=[3])
    open_issues_count: SafeInteger = Field(
        alias="openIssuesCount",
        description="Number of open issues reported by the provider.",
        examples=[1],
    )
    archived: bool = Field(strict=True, description="Whether the repository is archived.", examples=[False])
    created_at: CanonicalTimestamp = Field(
        alias="createdAt",
        description="Repository creation time in canonical UTC millisecond form.",
        examples=["2026-01-15T10:30:00.000Z"],
    )
    updated_at: CanonicalTimestamp = Field(
        alias="updatedAt",
        description="Repository update time in canonical UTC millisecond form.",
        examples=["2026-01-16T11:45:00.000Z"],
    )
    pushed_at: CanonicalTimestamp | None = Field(
        alias="pushedAt",
        description="Most recent push time in canonical UTC millisecond form, when present.",
        examples=["2026-01-16T11:40:00.000Z"],
    )
    default_branch: str = Field(
        alias="defaultBranch",
        min_length=1,
        strict=True,
        description="Default branch name.",
        examples=["main"],
    )
    license: str | None = Field(description="SPDX license identifier, when present.", examples=["MIT"])
    topics: list[str] = Field(
        json_schema_extra={"uniqueItems": True},
        description="Unique repository topics in portable scalar-value order.",
        examples=[["api", "python"]],
    )
    disabled: bool = Field(strict=True, description="Whether the repository is disabled.", examples=[False])


class GitHubActivity(GitHubModel):
    id: SafeInteger = Field(description="Repository activity identifier.", examples=[123456])
    actor: str | None = Field(description="Actor login, or null for a deleted actor.", examples=["octocat"])
    actor_avatar_url: HttpURL | None = Field(
        alias="actorAvatarUrl",
        description="Absolute HTTP(S) actor avatar URL, or null for a deleted actor.",
        examples=["https://avatars.example.test/u/583231"],
    )
    ref: str = Field(
        min_length=1,
        strict=True,
        description="Repository reference associated with the activity.",
        examples=["refs/heads/main"],
    )
    timestamp: CanonicalTimestamp = Field(
        description="Activity time in canonical UTC millisecond form.",
        examples=["2026-01-16T11:45:00.000Z"],
    )
    activity_type: str = Field(
        alias="activityType",
        min_length=1,
        strict=True,
        description="Provider activity type; values are intentionally open.",
        examples=["push"],
    )


class GitHubLanguage(GitHubModel):
    name: str = Field(min_length=1, strict=True, description="Repository language name.", examples=["Python"])
    bytes: SafeInteger = Field(description="Number of bytes attributed to the language.", examples=[12345])


class GitHubCommit(GitHubModel):
    sha: str = Field(
        pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$",
        strict=True,
        description="Lowercase 40- or 64-character hexadecimal commit identifier.",
        examples=["0123456789abcdef0123456789abcdef01234567"],
    )


class GitHubTag(GitHubModel):
    name: str = Field(min_length=1, strict=True, description="Repository tag name.", examples=["v1.0.0"])
    commit: GitHubCommit


class GitHubRepositoryPage(GitHubModel):
    repos: list[GitHubRepositorySummary] = Field(max_length=100)
    count: int = Field(ge=0, le=100, strict=True, description="Number of repositories in this page.", examples=[1])


class GitHubActivityPage(GitHubModel):
    activities: list[GitHubActivity] = Field(max_length=100)
    count: int = Field(ge=0, le=100, strict=True, description="Number of activities in this page.", examples=[1])


class GitHubLanguages(GitHubModel):
    languages: list[GitHubLanguage]


class GitHubTagPage(GitHubModel):
    tags: list[GitHubTag] = Field(max_length=100)
    count: int = Field(ge=0, le=100, strict=True, description="Number of tags in this page.", examples=[1])
