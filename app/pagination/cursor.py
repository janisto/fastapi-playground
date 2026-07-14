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

    type: str
    value: str

    def encode(self) -> str:
        """
        Encode as URL-safe base64 without padding.
        """
        data = f"{self.type}:{self.value}"
        return base64.urlsafe_b64encode(data.encode()).rstrip(b"=").decode()


def decode_cursor(s: str) -> Cursor:
    """
    Decode URL-safe base64 cursor.
    """
    if not s:
        return Cursor(type="", value="")
    padding = _BASE64_BLOCK_SIZE - len(s) % _BASE64_BLOCK_SIZE
    if padding != _BASE64_BLOCK_SIZE:
        s += "=" * padding
    try:
        decoded = base64.b64decode(s.encode("ascii"), altchars=b"-_", validate=True).decode()
    except (binascii.Error, UnicodeError) as e:
        raise InvalidCursorError("invalid cursor format") from e
    try:
        cursor_type, value = decoded.split(":", maxsplit=1)
    except ValueError as e:
        raise InvalidCursorError("invalid cursor format") from e
    return Cursor(type=cursor_type, value=value)
