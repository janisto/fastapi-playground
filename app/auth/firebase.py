"""Strict Firebase bearer authentication for portable profile operations."""

import asyncio
import logging
import re
from dataclasses import dataclass

from fastapi import Request
from firebase_admin import auth
from firebase_admin.auth import (
    CertificateFetchError,
    ExpiredIdTokenError,
    InvalidIdTokenError,
    RevokedIdTokenError,
    UserDisabledError,
)

from app.core.firebase import get_firebase_app
from app.core.problems import PortableProblem
from app.models.types import validate_opaque_id

logger = logging.getLogger(__name__)
_BEARER = re.compile(r"(?i:Bearer) +([A-Za-z0-9\-._~+/]+={0,})\Z")
_OPAQUE_ID_MAX_LENGTH = 128


@dataclass(frozen=True, slots=True)
class FirebaseUser:
    """Verified immutable Firebase principal."""

    uid: str


def _authorization_values(request: Request) -> list[str]:
    return [
        value.decode("latin1") for key, value in request.scope.get("headers", []) if key.lower() == b"authorization"
    ]


async def verify_firebase_token(request: Request) -> FirebaseUser:
    """Parse one token68 bearer credential and verify revocation with Firebase."""
    values = _authorization_values(request)
    if len(values) != 1 or "," in values[0]:
        raise PortableProblem("unauthorized", headers={"WWW-Authenticate": "Bearer"})
    match = _BEARER.fullmatch(values[0])
    if match is None:
        raise PortableProblem("unauthorized", headers={"WWW-Authenticate": "Bearer"})
    token = match.group(1)
    try:
        firebase_app = get_firebase_app()
    except Exception:  # noqa: BLE001 - initialization failures are controlled dependency outages
        logger.error("Firebase verifier initialization failed")  # noqa: TRY400 - do not log provider details
        raise PortableProblem("dependency_unavailable", headers={"Retry-After": "30"}) from None
    try:
        decoded_token = await asyncio.to_thread(
            auth.verify_id_token,
            token,
            app=firebase_app,
            check_revoked=True,
        )
    except ValueError, ExpiredIdTokenError, RevokedIdTokenError, UserDisabledError, InvalidIdTokenError:
        logger.warning("Firebase credential rejected")
        raise PortableProblem("unauthorized", headers={"WWW-Authenticate": "Bearer"}) from None
    except CertificateFetchError:
        logger.error("Firebase verifier dependency unavailable")  # noqa: TRY400 - do not log provider exception text
        raise PortableProblem("dependency_unavailable", headers={"Retry-After": "30"}) from None
    except Exception:  # noqa: BLE001 - unknown verifier failures must fail closed as dependency outages
        logger.error("Firebase verifier failed")  # noqa: TRY400 - credential failures must not emit traceback text
        raise PortableProblem("dependency_unavailable", headers={"Retry-After": "30"}) from None

    if not isinstance(decoded_token, dict):
        logger.error("Firebase verifier returned an invalid result")
        raise PortableProblem("dependency_unavailable", headers={"Retry-After": "30"})
    principal = decoded_token.get("sub")
    if not isinstance(principal, str) or not 1 <= len(principal) <= _OPAQUE_ID_MAX_LENGTH:
        raise PortableProblem("unauthorized", headers={"WWW-Authenticate": "Bearer"})
    try:
        validate_opaque_id(principal)
    except ValueError:
        raise PortableProblem("unauthorized", headers={"WWW-Authenticate": "Bearer"}) from None
    return FirebaseUser(uid=principal)
