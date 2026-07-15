from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response, status

from talaqi.identity.dependencies import DatabaseSession, build_auth_service
from talaqi.identity.rate_limits import AuthRateLimitAction, LazyAuthRateLimiter
from talaqi.identity.schemas import (
    AuthenticationResponse,
    LoginRequest,
    LogoutResponse,
    RegistrationRequest,
    RegistrationResponse,
)
from talaqi.identity.sessions import ACCESS_COOKIE_NAME
from talaqi.platform import ApiError
from talaqi.platform.errors import ErrorEnvelope

router = APIRouter(prefix="/api/v1/auth", tags=["identity"])
_AUTH_FAILURE: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Authentication failed.",
}
_INPUT_FAILURE: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Input was rejected.",
}
_RATE_LIMIT_FAILURE: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "The authentication request rate was exceeded.",
}


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="registerAccount",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: _INPUT_FAILURE,
        status.HTTP_429_TOO_MANY_REQUESTS: _RATE_LIMIT_FAILURE,
    },
)
async def register_account(
    body: RegistrationRequest, request: Request, session: DatabaseSession
) -> RegistrationResponse:
    limiter: LazyAuthRateLimiter = request.app.state.auth_rate_limits
    await limiter.check(
        AuthRateLimitAction.REGISTER,
        client_host=request.client.host if request.client else None,
        identifier=body.email,
    )
    await build_auth_service(request, session).register(**body.model_dump())
    return RegistrationResponse()


@router.post(
    "/login",
    response_model=AuthenticationResponse,
    operation_id="loginAccount",
    responses={
        status.HTTP_401_UNAUTHORIZED: _AUTH_FAILURE,
        status.HTTP_422_UNPROCESSABLE_CONTENT: _INPUT_FAILURE,
        status.HTTP_429_TOO_MANY_REQUESTS: _RATE_LIMIT_FAILURE,
    },
)
async def login_account(
    body: LoginRequest, request: Request, response: Response, session: DatabaseSession
) -> AuthenticationResponse:
    limiter: LazyAuthRateLimiter = request.app.state.auth_rate_limits
    await limiter.check(
        AuthRateLimitAction.LOGIN,
        client_host=request.client.host if request.client else None,
        identifier=body.identifier,
    )
    settings = request.app.state.settings_factory()
    result = await build_auth_service(request, session).login(body.identifier, body.password)
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        result.access_cookie,
        max_age=900,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return AuthenticationResponse(email_verified=result.principal.email_verified)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    operation_id="logoutAccount",
    responses={status.HTTP_401_UNAUTHORIZED: _AUTH_FAILURE},
)
async def logout_account(
    request: Request, response: Response, session: DatabaseSession
) -> LogoutResponse:
    encoded = request.cookies.get(ACCESS_COOKIE_NAME)
    if encoded is None:
        raise ApiError(
            code="authentication_required",
            message_key="errors.authentication_required",
            status_code=401,
        )
    await build_auth_service(request, session).logout(encoded)
    response.delete_cookie(
        ACCESS_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=request.app.state.settings_factory().cookie_secure,
        samesite="lax",
    )
    return LogoutResponse()
