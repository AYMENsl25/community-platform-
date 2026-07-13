from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from talaqi.platform.errors import (
    ApiError,
    ErrorDetail,
    ErrorEnvelope,
    FieldError,
    api_error_handler,
    http_error_handler,
    validation_error_handler,
)
from talaqi.platform.idempotency import (
    IdempotencyAcquisition,
    IdempotencyClaim,
    IdempotencyClaimLostError,
    IdempotencyCoordinator,
    IdempotencyRepository,
    hash_request_body,
)
from talaqi.platform.pagination import CursorCodec, CursorPage, CursorParams, CursorPosition
from talaqi.platform.request_ids import request_id_middleware


def register_platform_contracts(application: FastAPI) -> None:
    if getattr(application.state, "platform_contracts_registered", False):
        return
    application.state.platform_contracts_registered = True
    application.middleware("http")(request_id_middleware)
    application.add_exception_handler(ApiError, api_error_handler)  # pyright: ignore[reportArgumentType]
    application.add_exception_handler(
        RequestValidationError,
        validation_error_handler,  # pyright: ignore[reportArgumentType]
    )
    application.add_exception_handler(
        HTTPException,
        http_error_handler,  # pyright: ignore[reportArgumentType]
    )


__all__ = [
    "ApiError",
    "CursorCodec",
    "CursorPage",
    "CursorParams",
    "CursorPosition",
    "ErrorDetail",
    "ErrorEnvelope",
    "FieldError",
    "IdempotencyAcquisition",
    "IdempotencyClaim",
    "IdempotencyClaimLostError",
    "IdempotencyCoordinator",
    "IdempotencyRepository",
    "hash_request_body",
    "register_platform_contracts",
]
