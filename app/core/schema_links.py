"""
JSON Schema discovery link helpers.
"""

from starlette.requests import Request


def build_schema_url(request: Request, schema_path: str) -> str:
    """
    Build an absolute JSON Schema URL for a request.
    """
    return f"{str(request.base_url).rstrip('/')}{schema_path}"


def build_described_by_link(schema_path: str) -> str:
    """
    Build an RFC 8288 describedBy link value.
    """
    return f'<{schema_path}>; rel="describedBy"'
