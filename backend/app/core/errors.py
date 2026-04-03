from __future__ import annotations

from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models.api import ErrorResponse


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class BadRequestError(AppError):
    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(
            status_code=400,
            code="VALIDATION_ERROR",
            message=message,
            details=details,
        )


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message=message)


class ConflictError(AppError):
    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(
            status_code=409,
            code="CONFLICT",
            message=message,
            details=details,
        )


class ForbiddenError(AppError):
    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(
            status_code=403,
            code="FORBIDDEN",
            message=message,
            details=details,
        )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or f"req_{uuid4().hex[:10]}"


def _json_error(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        code=code,
        message=message,
        details=details,
        request_id=_request_id(request),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json", exclude_none=True),
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _json_error(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details: dict[str, object] | None = None
    if exc.errors():
        first_error = exc.errors()[0]
        location = [str(item) for item in first_error.get("loc", []) if item != "body"]
        details = {
            "field": ".".join(location) if location else None,
            "reason": first_error.get("msg"),
        }
    return _json_error(
        request=request,
        status_code=400,
        code="VALIDATION_ERROR",
        message="Invalid request.",
        details=details,
    )
