"""
Firestore document-key derivation for profile principals.
"""

import base64

from app.models.types import validate_opaque_id

_ENCODED_PREFIX = "~"


def firestore_profile_document_id(user_id: str) -> str:
    """
    Return an injective Firestore-safe key while preserving ordinary existing keys.
    """
    validate_opaque_id(user_id)
    if (
        user_id.startswith(_ENCODED_PREFIX)
        or "/" in user_id
        or user_id in {".", ".."}
        or (user_id.startswith("__") and user_id.endswith("__"))
    ):
        encoded = base64.urlsafe_b64encode(user_id.encode("utf-8")).rstrip(b"=").decode("ascii")
        return f"{_ENCODED_PREFIX}{encoded}"
    return user_id
