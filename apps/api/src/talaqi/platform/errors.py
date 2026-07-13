from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final, cast

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException

from talaqi.db.identifiers import generate_uuid7

VALIDATION_ERROR_CODE: Final = "validation_error"
VALIDATION_ERROR_MESSAGE_KEY: Final = "errors.validation"
_STABLE_VALUE = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_SAFE_FIELD_SEGMENT = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PUBLIC_FIELD_PATH = (
    r"^(?:body|query|path|header|cookie)"
    r"(?:\.[a-z][a-z0-9_]{0,63}(?:\.\*)?|\.\*)?$"
)
_VALIDATION_CODE = r"^[a-z][a-z0-9_.-]{0,127}$"
_FIELD_MESSAGE_KEY = r"^errors\.[a-z][a-z0-9_.-]{0,127}$"
_LOCATION_SOURCES = frozenset({"body", "query", "path", "header", "cookie"})


class FieldError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(min_length=1, max_length=136, pattern=_PUBLIC_FIELD_PATH)
    code: str = Field(min_length=1, max_length=128, pattern=_VALIDATION_CODE)
    message_key: str = Field(min_length=1, max_length=146, pattern=_FIELD_MESSAGE_KEY)


class ErrorDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message_key: str
    field_errors: tuple[FieldError, ...] = ()
    request_id: str


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    error: ErrorDetail


class ApiError(Exception):
    """A safe public API failure containing stable identifiers only."""

    def __init__(
        self,
        *,
        code: str,
        message_key: str,
        status_code: int,
        field_errors: Sequence[FieldError] = (),
    ) -> None:
        if _STABLE_VALUE.fullmatch(code) is None or _STABLE_VALUE.fullmatch(message_key) is None:
            raise ValueError("API errors require stable identifiers")
        if not 400 <= status_code <= 599:
            raise ValueError("API error status must be between 400 and 599")
        super().__init__(code)
        self.code = code
        self.message_key = message_key
        self.status_code = status_code
        self.field_errors = tuple(field_errors)


def request_id_for(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str):
        return request_id
    generated = str(generate_uuid7())
    request.state.request_id = generated
    return generated


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message_key: str,
    field_errors: Sequence[FieldError] = (),
) -> JSONResponse:
    request_id = request_id_for(request)
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message_key=message_key,
            field_errors=tuple(field_errors),
            request_id=request_id,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
        headers={"X-Request-ID": request_id},
    )


async def api_error_handler(request: Request, exception: ApiError) -> JSONResponse:
    return error_response(
        request,
        status_code=exception.status_code,
        code=exception.code,
        message_key=exception.message_key,
        field_errors=exception.field_errors,
    )


async def validation_error_handler(
    request: Request, exception: RequestValidationError
) -> JSONResponse:
    field_errors: dict[tuple[str, str, str], FieldError] = {}
    for item in exception.errors():
        raw_code = item.get("type")
        code = (
            raw_code
            if isinstance(raw_code, str) and _STABLE_VALUE.fullmatch(raw_code)
            else "invalid"
        )
        field = _safe_validation_field(
            request,
            item.get("loc", ()),
            code=code,
        )
        field_error = FieldError(
            field=field,
            code=code,
            message_key=f"errors.validation.{code}",
        )
        field_errors[(field_error.field, field_error.code, field_error.message_key)] = field_error
    safe_errors = sorted(
        field_errors.values(), key=lambda item: (item.field, item.code, item.message_key)
    )
    return error_response(
        request,
        status_code=422,
        code=VALIDATION_ERROR_CODE,
        message_key=VALIDATION_ERROR_MESSAGE_KEY,
        field_errors=safe_errors,
    )


def _safe_validation_field(request: Request, location: object, *, code: str) -> str:
    if not isinstance(location, (list, tuple)):
        return "body.*"
    parts = tuple(cast(Sequence[object], location))
    source_value = parts[0] if parts else None
    source = (
        source_value
        if isinstance(source_value, str) and source_value in _LOCATION_SOURCES
        else "body"
    )
    known_fields = _known_validation_fields(request, source)
    if len(parts) < 2 or code == "extra_forbidden":
        if len(parts) > 2:
            root_field = parts[1]
            if root_field in known_fields:
                return f"{source}.{root_field}.*"
        return f"{source}.*"
    root_field = parts[1]
    if root_field not in known_fields:
        return f"{source}.*"
    if len(parts) > 2:
        return f"{source}.{root_field}.*"
    return f"{source}.{root_field}"


def _known_validation_fields(request: Request, source: str) -> frozenset[str]:
    route = request.scope.get("route")
    if not isinstance(route, APIRoute):
        return frozenset()
    parameters = {
        "body": route.dependant.body_params,
        "query": route.dependant.query_params,
        "path": route.dependant.path_params,
        "header": route.dependant.header_params,
        "cookie": route.dependant.cookie_params,
    }[source]
    known: set[str] = set()
    for parameter in parameters:
        alias = parameter.alias
        if _SAFE_FIELD_SEGMENT.fullmatch(alias):
            known.add(alias)
        parameter_type = parameter.field_info.annotation
        if isinstance(parameter_type, type) and issubclass(parameter_type, BaseModel):
            for name, model_field in parameter_type.model_fields.items():
                public_name = model_field.alias or name
                if _SAFE_FIELD_SEGMENT.fullmatch(public_name):
                    known.add(public_name)
    return frozenset(known)


_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    400: ("bad_request", "errors.bad_request"),
    401: ("unauthorized", "errors.unauthorized"),
    403: ("forbidden", "errors.forbidden"),
    404: ("not_found", "errors.not_found"),
    405: ("method_not_allowed", "errors.method_not_allowed"),
    409: ("conflict", "errors.conflict"),
}


async def http_error_handler(request: Request, exception: HTTPException) -> JSONResponse:
    code, message_key = _HTTP_ERRORS.get(exception.status_code, ("http_error", "errors.http"))
    return error_response(
        request,
        status_code=exception.status_code,
        code=code,
        message_key=message_key,
    )
