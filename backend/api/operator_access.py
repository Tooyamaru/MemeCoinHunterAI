"""Fail-closed single-controller bearer access helper for future OAF mutation routes."""

from __future__ import annotations

import hmac


class OperatorAccessDenied(PermissionError):
    """Bounded authorization failure with no credential detail."""


def require_operator_bearer(*, authorization: str | None, configured_token: str | None) -> None:
    """Require an exact Bearer token match; missing configuration always denies."""

    if not isinstance(configured_token, str) or len(configured_token) < 24:
        raise OperatorAccessDenied("OPERATOR_ACCESS_UNAVAILABLE")
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        raise OperatorAccessDenied("OPERATOR_AUTH_REQUIRED")
    presented = authorization[7:]
    if not presented or not hmac.compare_digest(presented, configured_token):
        raise OperatorAccessDenied("OPERATOR_AUTH_INVALID")


__all__ = ["OperatorAccessDenied", "require_operator_bearer"]
