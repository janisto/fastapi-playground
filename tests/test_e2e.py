"""End-to-end tests for the FastAPI application."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from datetime import UTC


@pytest.fixture
def client() -> Generator[TestClient]:
    """Create a test client."""
    with patch("app.main.initialize_firebase"), patch("app.main.setup_logging"):
        yield TestClient(app)


@pytest.fixture
def mock_firebase_user() -> MagicMock:
    """Create a mock Firebase user."""
    user = MagicMock()
    user.uid = "test-user-123"
    user.email = "test@example.com"
    user.email_verified = True
    return user


class TestRootEndpoints:
    """Test root endpoints."""

    def test_root_endpoint(self, client: TestClient) -> None:
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Hello World"
        assert data["docs"] == "/api-docs"

    def test_health_check(self, client: TestClient) -> None:
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestProfileEndpoints:
    """Test profile endpoints."""

    @patch("app.routers.profile.verify_firebase_token")
    @patch("app.services.profile.profile_service.get_profile")
    @patch("app.services.profile.profile_service.create_profile")
    @patch("app.auth.firebase.get_firebase_app")
    def test_create_profile_success(
        self,
        mock_get_firebase_app: MagicMock,
        mock_create: MagicMock,
        mock_get: MagicMock,
        mock_verify: MagicMock,
        client: TestClient,
        mock_firebase_user: MagicMock,
    ) -> None:
        """Test successful profile creation."""
        # Setup Firebase mock
        mock_get_firebase_app.return_value = MagicMock()

        # Setup mocks
        mock_verify.return_value = mock_firebase_user
        mock_get.return_value = None  # No existing profile

        # Mock created profile
        from datetime import datetime

        from app.models.profile import Profile

        created_profile = Profile(
            id="test-user-123",
            firstname="John",
            lastname="Doe",
            email="john@example.com",
            phone_number="+1234567890",
            marketing=True,
            terms=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_create.return_value = created_profile

        # Test data
        profile_data = {
            "firstname": "John",
            "lastname": "Doe",
            "email": "john@example.com",
            "phone_number": "+1234567890",
            "marketing": True,
            "terms": True,
        }

        # Make request
        response = client.post("/profile/", json=profile_data, headers={"Authorization": "Bearer test-token"})

        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Profile created successfully"
        assert data["profile"]["firstname"] == "John"

    @patch("app.routers.profile.verify_firebase_token")
    @patch("app.services.profile.profile_service.get_profile")
    def test_create_profile_already_exists(
        self, mock_get: MagicMock, mock_verify: MagicMock, client: TestClient, mock_firebase_user: MagicMock
    ) -> None:
        """Test profile creation when profile already exists."""
        # Setup mocks
        mock_verify.return_value = mock_firebase_user

        from datetime import datetime

        from app.models.profile import Profile

        existing_profile = Profile(
            id=mock_firebase_user.uid,
            firstname="Jane",
            lastname="Doe",
            email="jane@example.com",
            phone_number="+1234567890",
            marketing=False,
            terms=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get.return_value = existing_profile

        # Test data
        profile_data = {
            "firstname": "John",
            "lastname": "Doe",
            "email": "john@example.com",
            "phone_number": "+1234567890",
            "marketing": True,
            "terms": True,
        }

        # Make request
        response = client.post("/profile/", json=profile_data, headers={"Authorization": "Bearer test-token"})

        # Assertions
        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"]

    @patch("app.routers.profile.verify_firebase_token")
    @patch("app.services.profile.profile_service.get_profile")
    def test_get_profile_success(
        self, mock_get: MagicMock, mock_verify: MagicMock, client: TestClient, mock_firebase_user: MagicMock
    ) -> None:
        """Test successful profile retrieval."""
        # Setup mocks
        mock_verify.return_value = mock_firebase_user

        from datetime import datetime

        from app.models.profile import Profile

        profile = Profile(
            id=mock_firebase_user.uid,
            firstname="John",
            lastname="Doe",
            email="john@example.com",
            phone_number="+1234567890",
            marketing=True,
            terms=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get.return_value = profile

        # Make request
        response = client.get("/profile/", headers={"Authorization": "Bearer test-token"})

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["profile"]["firstname"] == "John"

    @patch("app.routers.profile.verify_firebase_token")
    @patch("app.services.profile.profile_service.get_profile")
    def test_get_profile_not_found(
        self, mock_get: MagicMock, mock_verify: MagicMock, client: TestClient, mock_firebase_user: MagicMock
    ) -> None:
        """Test profile retrieval when profile doesn't exist."""
        # Setup mocks
        mock_verify.return_value = mock_firebase_user
        mock_get.return_value = None

        # Make request
        response = client.get("/profile/", headers={"Authorization": "Bearer test-token"})

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_unauthorized_access(self, client: TestClient) -> None:
        """Test accessing profile endpoints without authorization."""
        # Test create profile
        response = client.post("/profile/", json={})
        assert response.status_code == 403

        # Test get profile
        response = client.get("/profile/")
        assert response.status_code == 403

        # Test update profile
        response = client.put("/profile/", json={})
        assert response.status_code == 403

        # Test delete profile
        response = client.delete("/profile/")
        assert response.status_code == 403


class TestValidation:
    """Test input validation."""

    @patch("app.routers.profile.verify_firebase_token")
    def test_invalid_profile_data(
        self, mock_verify: MagicMock, client: TestClient, mock_firebase_user: MagicMock
    ) -> None:
        """Test profile creation with invalid data."""
        mock_verify.return_value = mock_firebase_user

        # Missing required fields
        invalid_data = {
            "firstname": "John",
            # Missing lastname, email, phone_number, terms
        }

        response = client.post("/profile/", json=invalid_data, headers={"Authorization": "Bearer test-token"})

        assert response.status_code == 422  # Validation error

    @patch("app.routers.profile.verify_firebase_token")
    def test_invalid_email_format(
        self, mock_verify: MagicMock, client: TestClient, mock_firebase_user: MagicMock
    ) -> None:
        """Test profile creation with invalid email format."""
        mock_verify.return_value = mock_firebase_user

        invalid_data = {
            "firstname": "John",
            "lastname": "Doe",
            "email": "invalid-email",  # Invalid email format
            "phone_number": "+1234567890",
            "marketing": True,
            "terms": True,
        }

        response = client.post("/profile/", json=invalid_data, headers={"Authorization": "Bearer test-token"})

        assert response.status_code == 422  # Validation error
