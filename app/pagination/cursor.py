"""
Cursor encoding/decoding for pagination.
"""

import base64
from dataclasses import dataclass


class InvalidCursorError(Exception):
    """
    Raised when cursor cannot be decoded.
    """


@dataclass
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
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    try:
        decoded = base64.urlsafe_b64decode(s.encode()).decode()
    except Exception as e:
        raise InvalidCursorError("invalid cursor format") from e
    parts = decoded.split(":", 1)
    if len(parts) != 2:
        raise InvalidCursorError("invalid cursor format")
    return Cursor(type=parts[0], value=parts[1])
