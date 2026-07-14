"""
Cursor encoding/decoding for pagination.
"""

import base64
import binascii
from dataclasses import dataclass

_BASE64_BLOCK_SIZE = 4


class InvalidCursorError(Exception):
    """
    Raised when cursor cannot be decoded.
    """


@dataclass(frozen=True, slots=True)
class Cursor:
    """
    Pagination cursor with type and value.
    """

    cursor_type: str
    value: str

    def encode(self) -> str:
        """
        Encode as URL-safe base64 without padding.
        """
        data = f"{self.cursor_type}:{self.value}"
        return base64.urlsafe_b64encode(data.encode()).rstrip(b"=").decode()


def decode_cursor(encoded_cursor: str) -> Cursor:
    """
    Decode URL-safe base64 cursor.
    """
    if not encoded_cursor:
        return Cursor(cursor_type="", value="")
    padding = _BASE64_BLOCK_SIZE - len(encoded_cursor) % _BASE64_BLOCK_SIZE
    if padding != _BASE64_BLOCK_SIZE:
        encoded_cursor += "=" * padding
    try:
        decoded = base64.b64decode(encoded_cursor.encode("ascii"), altchars=b"-_", validate=True).decode()
    except (binascii.Error, UnicodeError) as e:
        raise InvalidCursorError("invalid cursor format") from e
    try:
        cursor_type, value = decoded.split(":", maxsplit=1)
    except ValueError as e:
        raise InvalidCursorError("invalid cursor format") from e
    return Cursor(cursor_type=cursor_type, value=value)
