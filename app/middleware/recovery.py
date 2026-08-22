"""
Contain exceptions after FastAPI has rendered a controlled response.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class HandledExceptionMiddleware:
    """
    Prevent a completed exception response from being re-raised to the ASGI server.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        response_complete = False

        async def tracked_send(message: Message) -> None:
            nonlocal response_complete
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                response_complete = True

        try:
            await self.app(scope, receive, tracked_send)
        except Exception:
            if not response_complete or scope.get("portable.handled_exception") is not True:
                raise
