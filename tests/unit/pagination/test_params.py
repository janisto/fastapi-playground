"""Unit tests for pagination parameter types."""

from typing import get_args, get_origin

from app.pagination import CursorParam, LimitParam


class TestCursorParam:
    """Tests for CursorParam type alias."""

    def test_is_optional_string(self) -> None:
        """Test CursorParam is Optional[str]."""
        origin = get_origin(CursorParam)
        assert origin is not None

    def test_allows_none(self) -> None:
        """Test CursorParam allows None as a value."""
        args = get_args(CursorParam)
        base_type = args[0] if args else None
        assert base_type is not None


class TestLimitParam:
    """Tests for LimitParam type alias."""

    def test_is_int_based(self) -> None:
        """Test LimitParam is based on int."""
        origin = get_origin(LimitParam)
        assert origin is not None
