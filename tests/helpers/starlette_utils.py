"""
Starlette app utilities for isolated middleware tests.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any

from starlette.applications import Starlette

RouteHandler = Callable[..., Awaitable[Any]]
MiddlewareSpec = tuple[type, dict[str, Any]]


def build_starlette_app(
    routes: Sequence[tuple[str, RouteHandler, Sequence[str]]],
    middleware: Iterable[MiddlewareSpec] | None = None,
) -> Starlette:
    """
    Build a minimal Starlette app for tests.

    Parameters:
        routes: Tuples of (path, handler, methods).
        middleware: Optional iterable of (MiddlewareClass, kwargs dict).
    """
    app = Starlette()
    for path, handler, methods in routes:
        app.add_route(path, handler, methods=list(methods))
    if middleware:
        for mw_cls, mw_kwargs in middleware:
            app.add_middleware(mw_cls, **mw_kwargs)
    return app


__all__ = ["build_starlette_app"]
