"""
JSON Schema discovery link helpers.
"""


def build_described_by_link(schema_path: str) -> str:
    """
    Build an RFC 8288 describedBy link value.
    """
    return f'<{schema_path}>; rel="describedBy"'
