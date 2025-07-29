"""Unit tests for Firebase authentication."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.firebase import FirebaseUser, verify_firebase_token


class TestFirebaseUser:
    """Test FirebaseUser class."""

    def test_firebase_user_creation(self) -> None:
        """Test creating a FirebaseUser instance."""
        user = FirebaseUser(uid="test-user-123", email="test@example.com", email_verified=True)

        assert user.uid == "test-user-123"
        assert user.email == "test@example.com"
        assert user.email_verified is True

    def test_firebase_user_defaults(self) -> None:
        """Test FirebaseUser with default values."""
        user = FirebaseUser(uid="test-user-123")

        assert user.uid == "test-user-123"
        assert user.email is None
        assert user.email_verified is False


class TestVerifyFirebaseToken:
    """Test Firebase token verification."""

    @patch("app.auth.firebase.auth.verify_id_token")
    @patch("app.auth.firebase.get_firebase_app")
    @pytest.mark.asyncio
    async def test_verify_token_success(self, mock_get_app: MagicMock, mock_verify_token: MagicMock) -> None:
        """Test successful token verification."""
        # Setup mocks
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        mock_verify_token.return_value = {"uid": "test-user-123", "email": "test@example.com", "email_verified": True}

        # Create test credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")

        # Call function
        user = await verify_firebase_token(credentials)

        # Assertions
        assert isinstance(user, FirebaseUser)
        assert user.uid == "test-user-123"
        assert user.email == "test@example.com"
        assert user.email_verified is True

        # Verify mocks were called correctly
        mock_verify_token.assert_called_once_with("test-token", app=mock_app)

    @patch("app.auth.firebase.auth.verify_id_token")
    @patch("app.auth.firebase.get_firebase_app")
    @pytest.mark.asyncio
    async def test_verify_token_missing_uid(self, mock_get_app: MagicMock, mock_verify_token: MagicMock) -> None:
        """Test token verification with missing UID."""
        # Setup mocks
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        mock_verify_token.return_value = {
            # Missing uid
            "email": "test@example.com",
            "email_verified": True,
        }

        # Create test credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401
        assert "missing user ID" in exc_info.value.detail

    @patch("app.auth.firebase.auth.verify_id_token")
    @patch("app.auth.firebase.get_firebase_app")
    @pytest.mark.asyncio
    async def test_verify_token_invalid_token(self, mock_get_app: MagicMock, mock_verify_token: MagicMock) -> None:
        """Test token verification with invalid token."""
        from firebase_admin.auth import InvalidIdTokenError

        # Setup mocks
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        mock_verify_token.side_effect = InvalidIdTokenError("Invalid token", None)

        # Create test credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token"

    @patch("app.auth.firebase.auth.verify_id_token")
    @patch("app.auth.firebase.get_firebase_app")
    @pytest.mark.asyncio
    async def test_verify_token_expired_token(self, mock_get_app: MagicMock, mock_verify_token: MagicMock) -> None:
        """Test token verification with expired token."""
        from firebase_admin.auth import ExpiredIdTokenError

        # Setup mocks
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        mock_verify_token.side_effect = ExpiredIdTokenError("Token expired", None)

        # Create test credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired-token")

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token expired"

    @patch("app.auth.firebase.auth.verify_id_token")
    @patch("app.auth.firebase.get_firebase_app")
    @pytest.mark.asyncio
    async def test_verify_token_revoked_token(self, mock_get_app: MagicMock, mock_verify_token: MagicMock) -> None:
        """Test token verification with revoked token."""
        from firebase_admin.auth import RevokedIdTokenError

        # Setup mocks
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        mock_verify_token.side_effect = RevokedIdTokenError("Token revoked")

        # Create test credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="revoked-token")

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token revoked"

    @patch("app.auth.firebase.auth.verify_id_token")
    @patch("app.auth.firebase.get_firebase_app")
    @pytest.mark.asyncio
    async def test_verify_token_generic_error(self, mock_get_app: MagicMock, mock_verify_token: MagicMock) -> None:
        """Test token verification with generic error."""
        # Setup mocks
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        mock_verify_token.side_effect = Exception("Generic error")

        # Create test credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="error-token")

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication failed"
