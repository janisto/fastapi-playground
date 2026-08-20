"""Canonical opaque Base64URL pagination cursors."""

import base64
import binascii
import json
import re
from typing import Any

MAX_CURSOR_LENGTH = 2048
_CANONICAL_BASE64URL = re.compile(r"[A-Za-z0-9_-]+\Z")


class InvalidCursorError(Exception):
    """Raised when a cursor is malformed, noncanonical, stale, or out of scope."""


def encode_cursor(state: dict[str, Any]) -> str:
    """Encode a validated public cursor state canonically."""
    payload = json.dumps(state, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    cursor = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    if len(cursor) > MAX_CURSOR_LENGTH:
        raise InvalidCursorError("cursor exceeds maximum length")
    return cursor


def decode_cursor(encoded_cursor: str) -> dict[str, Any]:
    """Decode and canonicalize a public cursor object."""
    if (
        not encoded_cursor
        or len(encoded_cursor) > MAX_CURSOR_LENGTH
        or _CANONICAL_BASE64URL.fullmatch(encoded_cursor) is None
    ):
        raise InvalidCursorError("invalid cursor format")
    padding = "=" * (-len(encoded_cursor) % 4)
    try:
        raw = base64.b64decode((encoded_cursor + padding).encode("ascii"), altchars=b"-_", validate=True)
        state = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeError, ValueError) as error:
        raise InvalidCursorError("invalid cursor format") from error
    if not isinstance(state, dict) or encode_cursor(state) != encoded_cursor:
        raise InvalidCursorError("invalid cursor format")
    return state
