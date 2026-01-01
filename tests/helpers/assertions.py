"""
Assertion helpers for tests.
"""

from httpx import Response


def assert_error_response(response: Response, expected_status: int) -> dict:
    """
    Assert response matches RFC 9457 Problem Details schema.

    Args:
        response: The HTTP response to validate.
        expected_status: Expected HTTP status code.

    Returns:
        The parsed JSON body for further assertions.
    """
    assert response.status_code == expected_status
    body = response.json()
    assert "title" in body, f"Missing 'title': {body}"
    assert isinstance(body["title"], str)
    assert "status" in body, f"Missing 'status': {body}"
    assert body["status"] == expected_status
    return body


def assert_validation_error(response: Response, field: str) -> dict:
    """
    Assert response is a 422 validation error mentioning the specified field.

    Args:
        response: The HTTP response to validate.
        field: Field name expected to be mentioned in validation errors.

    Returns:
        The parsed JSON body for further assertions.
    """
    assert response.status_code == 422
    body = response.json()
    assert "errors" in body
    errors = body["errors"]
    assert isinstance(errors, list), f"Expected list of errors: {errors}"
    field_mentioned = any(field in str(err.get("location", "")) for err in errors)
    assert field_mentioned, f"Field '{field}' not found in validation errors: {errors}"
    return body
