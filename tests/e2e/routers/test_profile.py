"""
E2E tests for profile endpoints against Firebase emulators.

These tests verify the complete flow including real Firestore operations.
Requires Firebase emulators to be running.
"""

BASE_URL = "/profile"


class TestProfileE2EFlow:
    """
    End-to-end tests for profile CRUD operations.

    These tests use real Firebase emulators and verify data persistence.
    Note: Auth is still mocked since we need valid Firebase tokens.
    """

    # NOTE: E2E tests pending Firebase Auth emulator token generation configuration
