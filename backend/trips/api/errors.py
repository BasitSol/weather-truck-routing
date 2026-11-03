"""One error envelope for every non-2xx response (API.md §2.3)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from rest_framework import exceptions, status
from rest_framework.response import Response

log = logging.getLogger(__name__)


class ApiError(exceptions.APIException):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message, code)
        self.status_code = status_code
        self.error_code = code
        self.message = message


def envelope(code: str, message: str, fields: dict[str, list[str]] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return {"error": body}


def _flatten(detail: Any, prefix: str = "") -> dict[str, list[str]]:
    """{'origin': {'lat': ['…']}} → {'origin.lat': ['…'], 'origin': ['…']} so the UI can find either."""
    if isinstance(detail, dict):
        out: dict[str, list[str]] = {}
        for key, value in detail.items():
            name = key if key != "non_field_errors" or not prefix else prefix
            name = f"{prefix}.{name}" if prefix and name != prefix else name
            for k, v in _flatten(value, name).items():
                out.setdefault(k, []).extend(v)
                top = k.split(".")[0]
                if top != k:
                    out.setdefault(top, []).extend(v)
        return out
    if isinstance(detail, list):
        messages = [str(d) for d in detail if not isinstance(d, dict | list)]
        nested = [d for d in detail if isinstance(d, dict | list)]
        out = {prefix: messages} if messages else {}
        for d in nested:
            for k, v in _flatten(d, prefix).items():
                out.setdefault(k, []).extend(v)
        return out
    return {prefix: [str(detail)]}


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    if isinstance(exc, ApiError):
        return Response(envelope(exc.error_code, exc.message), status=exc.status_code)
    if isinstance(exc, exceptions.ValidationError):
        fields = _flatten(exc.detail)
        first = next(iter(fields.values()), ["Invalid input."])[0]
        return Response(envelope("validation_error", first, fields), status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, exceptions.Throttled):
        headers = {"Retry-After": str(exc.wait)} if exc.wait else {}
        return Response(
            envelope("throttled", "Too many requests. Wait a moment and try again."),
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers=headers,
        )
    if isinstance(exc, exceptions.APIException):
        return Response(envelope(str(exc.default_code), str(exc.detail)), status=exc.status_code)

    request_id = uuid.uuid4().hex[:12]
    log.exception("unhandled error request_id=%s", request_id, exc_info=exc)
    return Response(
        envelope("internal_error", f"Something went wrong (request {request_id})."),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
