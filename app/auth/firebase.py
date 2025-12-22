"""
Firebase Authentication utilities.
"""

import asyncio
import logging
from dataclasses import dataclass

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth
from firebase_admin.auth import ExpiredIdTokenError, InvalidIdTokenError, RevokedIdTokenError, UserDisabledError

from app.core.firebase import get_firebase_app

logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()


@dataclass(frozen=True, slots=True)
class FirebaseUser:
    """
    Authenticated Firebase user extracted from token.
    """

    uid: str
    email: str | None = None
    email_verified: bool = False


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> FirebaseUser:
    """
    Verify Firebase ID token and return user information.

    Args:
        credentials: Bearer token credentials from request header

    Returns:
        FirebaseUser: Authenticated user information

    Raises:
        HTTPException: If token is invalid, expired, or revoked
    """
    token = credentials.credentials

    try:
        # Get Firebase app instance
        app = get_firebase_app()

        # Verify the ID token with revocation check
        # Run in thread pool to avoid blocking the event loop (sync Firebase SDK call)
        decoded_token = await asyncio.to_thread(auth.verify_id_token, token, app=app, check_revoked=True)

        # Extract user information
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        email_verified = decoded_token.get("email_verified", False)

        if not uid:
            logger.warning("Invalid token: missing user ID")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug("Successfully authenticated user", extra={"user_id": uid})

        return FirebaseUser(
            uid=uid,
            email=email,
            email_verified=email_verified,
        )

    except HTTPException:
        # Re-raise HTTPException without modification
        raise
    except ExpiredIdTokenError:
        logger.warning("Expired Firebase ID token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except RevokedIdTokenError:
        logger.warning("Revoked Firebase ID token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except UserDisabledError:
        logger.warning("Disabled Firebase user account")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except InvalidIdTokenError:
        logger.warning("Invalid Firebase ID token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except Exception:
        logger.exception("Error verifying Firebase token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
