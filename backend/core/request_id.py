"""Lightweight request correlation middleware."""

from contextvars import ContextVar
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.core.logging import get_logger

REQUEST_ID_HEADER = "X-Request-ID"
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
logger = get_logger()


def get_request_id() -> str:
    """Return the request ID for the current log/request context."""

    return _request_id.get()


def _incoming_request_id(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name.lower() == REQUEST_ID_HEADER.lower().encode():
            candidate = value.decode("latin-1").strip()
            if candidate and len(candidate) <= 128:
                return candidate
    return None


class RequestIdMiddleware:
    """Accept or generate a request ID and return it on every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope) or uuid4().hex
        token = _request_id.set(request_id)
        scope.setdefault("state", {})["request_id"] = request_id
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER.lower().encode(), request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
            logger.info(
                "http.request",
                extra={
                    "method": scope.get("method", "-"),
                    "path": scope.get("path", "-"),
                    "status_code": status_code,
                },
            )
        except Exception:
            logger.exception(
                "http.request_failed",
                extra={"method": scope.get("method", "-"), "path": scope.get("path", "-")},
            )
            raise
        finally:
            _request_id.reset(token)
