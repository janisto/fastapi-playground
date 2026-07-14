"""Unit tests for cursor encoding/decoding."""

import pytest

from app.pagination import MAX_CURSOR_LENGTH, Cursor, InvalidCursorError, decode_cursor


class TestCursor:
    """Tests for Cursor dataclass."""

    def test_encode_simple(self) -> None:
        """Test encoding a simple cursor."""
        cursor = Cursor(cursor_type="id", value="123")
        encoded = cursor.encode()
        assert encoded == "aWQ6MTIz"

    def test_encode_with_special_characters(self) -> None:
        """Test encoding cursor with special characters."""
        cursor = Cursor(cursor_type="timestamp", value="2025-01-01T00:00:00Z")
        encoded = cursor.encode()
        assert "+" not in encoded
        assert "/" not in encoded
        assert "=" not in encoded

    def test_encode_empty_value(self) -> None:
        """Test encoding cursor with empty value."""
        cursor = Cursor(cursor_type="id", value="")
        encoded = cursor.encode()
        decoded = decode_cursor(encoded)
        assert decoded.cursor_type == "id"
        assert decoded.value == ""


class TestDecodeCursor:
    """Tests for decode_cursor function."""

    def test_decode_empty_string(self) -> None:
        """Test decoding empty string returns empty cursor."""
        cursor = decode_cursor("")
        assert cursor.cursor_type == ""
        assert cursor.value == ""

    def test_decode_valid_cursor(self) -> None:
        """Test decoding a valid cursor."""
        original = Cursor(cursor_type="id", value="abc123")
        encoded = original.encode()
        decoded = decode_cursor(encoded)
        assert decoded.cursor_type == "id"
        assert decoded.value == "abc123"

    def test_decode_with_colon_in_value(self) -> None:
        """Test decoding cursor with colon in value."""
        original = Cursor(cursor_type="compound", value="2025-01-01:12345")
        encoded = original.encode()
        decoded = decode_cursor(encoded)
        assert decoded.cursor_type == "compound"
        assert decoded.value == "2025-01-01:12345"

    def test_decode_invalid_base64(self) -> None:
        """Test decoding invalid base64 raises InvalidCursorError."""
        with pytest.raises(InvalidCursorError, match="invalid cursor format"):
            decode_cursor("!!!invalid!!!")

    def test_decode_oversized_cursor(self) -> None:
        """Oversized cursors use the same malformed-cursor error boundary."""
        with pytest.raises(InvalidCursorError, match="cursor exceeds maximum length"):
            decode_cursor("x" * (MAX_CURSOR_LENGTH + 1))

    def test_decode_missing_separator(self) -> None:
        """Test decoding cursor without type:value separator raises error."""
        import base64

        invalid = base64.urlsafe_b64encode(b"nocolon").rstrip(b"=").decode()
        with pytest.raises(InvalidCursorError, match="invalid cursor format"):
            decode_cursor(invalid)

    def test_roundtrip_various_types(self) -> None:
        """Test encode/decode roundtrip with various cursor types."""
        test_cases = [
            ("id", "12345"),
            ("timestamp", "1735689600"),
            ("created_at", "2025-01-01T00:00:00+00:00"),
            ("composite", "user_123:1735689600"),
            ("unicode", "hello_世界"),
        ]
        for cursor_type, cursor_value in test_cases:
            original = Cursor(cursor_type=cursor_type, value=cursor_value)
            encoded = original.encode()
            decoded = decode_cursor(encoded)
            assert decoded.cursor_type == cursor_type, f"Failed for type: {cursor_type}"
            assert decoded.value == cursor_value, f"Failed for value: {cursor_value}"

    def test_decode_handles_padding_variations(self) -> None:
        """Test that decode handles base64 strings with various padding needs."""
        test_cases = [
            Cursor(cursor_type="a", value="b"),
            Cursor(cursor_type="ab", value="cd"),
            Cursor(cursor_type="abc", value="def"),
            Cursor(cursor_type="abcd", value="efgh"),
        ]
        for original in test_cases:
            encoded = original.encode()
            decoded = decode_cursor(encoded)
            assert decoded == original
