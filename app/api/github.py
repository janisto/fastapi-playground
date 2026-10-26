"""Public credential-free GitHub projection routes."""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Path, Query, Response

from app.core.constants import API_V1_PREFIX
from app.core.portable_http import PortableRoute
from app.core.problems import PortableProblem
from app.dependencies import GitHubServiceDependency
from app.models.github import (
    GitHubActivityPage,
    GitHubLanguages,
    GitHubOwner,
    GitHubRepository,
    GitHubRepositoryPage,
    GitHubTagPage,
)
from app.pagination import InvalidCursorError, build_link_header

OwnerPath = Annotated[
    str,
    Path(
        min_length=1,
        max_length=39,
        pattern=r"^(?:[A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9_-]{0,37}[A-Za-z0-9])$",
        description="Safe GitHub owner path segment",
    ),
]
RepoPath = Annotated[
    str,
    Path(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Safe non-dot-only GitHub repository path segment",
    ),
]
LimitQuery = Annotated[int, Query(ge=1, le=100, description="Entries per provider page")]
CursorQuery = Annotated[str | None, Query(min_length=1, max_length=2048, description="Opaque pagination cursor")]

router = APIRouter(prefix=f"{API_V1_PREFIX}/github", tags=["GitHub"], route_class=PortableRoute)


def _validate_repo(repo: str) -> None:
    if all(character == "." for character in repo):
        raise PortableProblem(
            "validation_failed",
            errors=[{"detail": "Request field is invalid"}],
        )


def _pagination_link(path: str, limit: int, next_cursor: str | None, prev_cursor: str | None) -> str:
    return build_link_header(path, {"limit": str(limit)}, next_cursor, prev_cursor)


@router.get(
    "/owners/{owner}",
    response_model=GitHubOwner,
    summary="Get a GitHub owner",
    description=(
        "Reads selected public owner fields anonymously from GitHub. Caller and server credentials are never "
        "forwarded. Returns 404 for a missing owner; quota, upstream, and deadline failures use the "
        "documented error codes. The server never retries automatically."
    ),
    operation_id="getGitHubOwner",
)
async def get_github_owner(owner: OwnerPath, service: GitHubServiceDependency) -> GitHubOwner:
    return await service.get_owner(owner)


@router.get(
    "/owners/{owner}/repos",
    response_model=GitHubRepositoryPage,
    summary="List GitHub owner repositories",
    description=(
        "Reads one provider-ordered page of public repositories without GitHub credentials. Follow next/prev "
        "HTTP Link targets and treat cursors as opaque and scoped to this owner and effective limit. Private "
        "repositories are never exposed; quota, upstream, and deadline failures are not retried by the "
        "server."
    ),
    operation_id="listGitHubOwnerRepositories",
)
async def list_github_owner_repositories(
    owner: OwnerPath,
    service: GitHubServiceDependency,
    response: Response,
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
) -> GitHubRepositoryPage:
    try:
        page, next_cursor, prev_cursor = await service.list_owner_repositories(owner, limit, cursor)
    except InvalidCursorError as error:
        raise PortableProblem("invalid_request") from error
    link = _pagination_link(f"/v1/github/owners/{quote(owner, safe='')}/repos", limit, next_cursor, prev_cursor)
    if link:
        response.headers["Link"] = link
    return page


@router.get(
    "/repos/{owner}/{repo}",
    response_model=GitHubRepository,
    summary="Get a GitHub repository",
    description=(
        "Reads one repository anonymously after checking public visibility. Missing or non-public resources "
        "return 404 github_not_found. Caller credentials are never forwarded. The bounded upstream request "
        "can fail with quota, upstream, or deadline errors and is never retried automatically."
    ),
    operation_id="getGitHubRepository",
)
async def get_github_repository(owner: OwnerPath, repo: RepoPath, service: GitHubServiceDependency) -> GitHubRepository:
    _validate_repo(repo)
    return await service.get_repository(owner, repo)


@router.get(
    "/repos/{owner}/{repo}/activity",
    response_model=GitHubActivityPage,
    summary="List GitHub repository activity",
    description=(
        "Reads one newest-first public activity page after a repository visibility check. Follow next/prev "
        "HTTP Link targets; cursors are opaque and scoped to this repository and effective limit. No "
        "authentication or mutation; upstream quota and deadline failures are returned without automatic "
        "retries."
    ),
    operation_id="listGitHubRepositoryActivity",
)
async def list_github_repository_activity(
    owner: OwnerPath,
    repo: RepoPath,
    service: GitHubServiceDependency,
    response: Response,
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
) -> GitHubActivityPage:
    _validate_repo(repo)
    try:
        page, next_cursor, prev_cursor = await service.list_repository_activity(owner, repo, limit, cursor)
    except InvalidCursorError as error:
        raise PortableProblem("invalid_request") from error
    path = f"/v1/github/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/activity"
    link = _pagination_link(path, limit, next_cursor, prev_cursor)
    if link:
        response.headers["Link"] = link
    return page


@router.get(
    "/repos/{owner}/{repo}/languages",
    response_model=GitHubLanguages,
    summary="List GitHub repository languages",
    description=(
        "Reads public repository language byte counts after a visibility check. Results are sorted by "
        "descending byte count, then Unicode scalar-value name; this result is not paginated. No credentials "
        "or mutation; upstream quota and deadline failures are returned without automatic retries."
    ),
    operation_id="listGitHubRepositoryLanguages",
)
async def list_github_repository_languages(
    owner: OwnerPath,
    repo: RepoPath,
    service: GitHubServiceDependency,
) -> GitHubLanguages:
    _validate_repo(repo)
    return await service.list_repository_languages(owner, repo)


@router.get(
    "/repos/{owner}/{repo}/tags",
    response_model=GitHubTagPage,
    summary="List GitHub repository tags",
    description=(
        "Reads one provider-ordered public tag page after a repository visibility check. Follow next/prev "
        "HTTP Link targets and keep cursors scoped to this repository and effective limit. Tags are provider "
        "data, not a guarantee of release versions. No credentials or mutation; the server never retries "
        "automatically."
    ),
    operation_id="listGitHubRepositoryTags",
)
async def list_github_repository_tags(
    owner: OwnerPath,
    repo: RepoPath,
    service: GitHubServiceDependency,
    response: Response,
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
) -> GitHubTagPage:
    _validate_repo(repo)
    try:
        page, next_cursor, prev_cursor = await service.list_repository_tags(owner, repo, limit, cursor)
    except InvalidCursorError as error:
        raise PortableProblem("invalid_request") from error
    path = f"/v1/github/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/tags"
    link = _pagination_link(path, limit, next_cursor, prev_cursor)
    if link:
        response.headers["Link"] = link
    return page
