"""RFC 8288 Link header builder."""

from urllib.parse import urlencode


def build_link_header(
    base_url: str,
    query_params: dict[str, str],
    next_cursor: str | None,
    prev_cursor: str | None,
) -> str:
    """
    Build Link header preserving query params.

    Args:
        base_url: Base URL path for the resource
        query_params: Existing query parameters to preserve
        next_cursor: Cursor for next page, if available
        prev_cursor: Cursor for previous page, if available

    Returns:
        RFC 8288 compliant Link header value
    """
    links = []
    if next_cursor:
        params = {**query_params, "cursor": next_cursor}
        links.append(f'<{base_url}?{urlencode(params)}>; rel="next"')
    if prev_cursor:
        params = {**query_params, "cursor": prev_cursor}
        links.append(f'<{base_url}?{urlencode(params)}>; rel="prev"')
    return ", ".join(links)
