"""Firebase Authentication utilities."""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth
from firebase_admin.auth import ExpiredIdTokenError, InvalidIdTokenError, RevokedIdTokenError

from app.core.firebase import get_firebase_app

logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()


class FirebaseUser:
    """Represents an authenticated Firebase user."""

    def __init__(self, uid: str, email: str | None = None, email_verified: bool = False) -> None:
        self.uid = uid
        self.email = email
        self.email_verified = email_verified


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
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

        # Verify the ID token
        decoded_token = auth.verify_id_token(token, app=app)

        # Extract user information
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        email_verified = decoded_token.get("email_verified", False)

        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"Successfully authenticated user: {uid}")

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
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except RevokedIdTokenError:
        logger.warning("Revoked Firebase ID token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidIdTokenError:
        logger.warning("Invalid Firebase ID token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
