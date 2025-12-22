"""
Unit tests for base exception classes.
"""

from app.exceptions.base import ConflictError, DomainError, NotFoundError


class TestDomainError:
    """
    Tests for DomainError base class.
    """

    def test_default_values(self) -> None:
        """
        Verify default status_code and detail.
        """
        err = DomainError()
        assert err.status_code == 500
        assert err.detail == "Internal error"

    def test_custom_detail(self) -> None:
        """
        Verify custom detail message overrides default.
        """
        err = DomainError("Custom message")
        assert err.detail == "Custom message"
        assert err.status_code == 500

    def test_exception_message(self) -> None:
        """
        Verify exception message matches detail.
        """
        err = DomainError("Test error")
        assert str(err) == "Test error"

    def test_default_exception_message(self) -> None:
        """
        Verify default exception message.
        """
        err = DomainError()
        assert str(err) == "Internal error"

    def test_default_headers_is_none(self) -> None:
        """
        Verify headers defaults to None.
        """
        err = DomainError()
        assert err.headers is None

    def test_custom_headers(self) -> None:
        """
        Verify custom headers can be set.
        """
        err = DomainError(headers={"Retry-After": "60"})
        assert err.headers == {"Retry-After": "60"}

    def test_headers_with_custom_detail(self) -> None:
        """
        Verify both detail and headers work together.
        """
        err = DomainError(detail="Rate limited", headers={"Retry-After": "120"})
        assert err.detail == "Rate limited"
        assert err.headers == {"Retry-After": "120"}


class TestNotFoundError:
    """
    Tests for NotFoundError.
    """

    def test_status_code_is_404(self) -> None:
        """
        Verify status_code is 404.
        """
        err = NotFoundError()
        assert err.status_code == 404

    def test_default_detail(self) -> None:
        """
        Verify default detail message.
        """
        err = NotFoundError()
        assert err.detail == "Resource not found"

    def test_custom_detail(self) -> None:
        """
        Verify custom detail overrides default.
        """
        err = NotFoundError("Item not found")
        assert err.detail == "Item not found"
        assert err.status_code == 404

    def test_inherits_from_domain_error(self) -> None:
        """
        Verify inheritance from DomainError.
        """
        err = NotFoundError()
        assert isinstance(err, DomainError)


class TestConflictError:
    """
    Tests for ConflictError.
    """

    def test_status_code_is_409(self) -> None:
        """
        Verify status_code is 409.
        """
        err = ConflictError()
        assert err.status_code == 409

    def test_default_detail(self) -> None:
        """
        Verify default detail message.
        """
        err = ConflictError()
        assert err.detail == "Resource conflict"

    def test_custom_detail(self) -> None:
        """
        Verify custom detail overrides default.
        """
        err = ConflictError("Duplicate entry")
        assert err.detail == "Duplicate entry"
        assert err.status_code == 409

    def test_inherits_from_domain_error(self) -> None:
        """
        Verify inheritance from DomainError.
        """
        err = ConflictError()
        assert isinstance(err, DomainError)
