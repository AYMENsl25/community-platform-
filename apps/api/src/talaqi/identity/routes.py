from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from talaqi.identity.dependencies import DatabaseSession, build_auth_service
from talaqi.identity.models import LoginResult, SessionBundle
from talaqi.identity.rate_limits import AuthRateLimitAction, LazyAuthRateLimiter
from talaqi.identity.schemas import (
    AcceptedResponse,
    AuthenticationResponse,
    ConfirmedResponse,
    LoginRequest,
    LogoutResponse,
    PasswordResetConfirm,
    RecoveryConfirm,
    RecoveryRequest,
    RefreshedResponse,
    RegistrationRequest,
    RegistrationResponse,
    RevokedResponse,
    SessionResponse,
    SessionsResponse,
)
from talaqi.identity.sessions import (
    ACCESS_COOKIE_NAME,
    ACCESS_LIFETIME_SECONDS,
    CSRF_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    REFRESH_LIFETIME_SECONDS,
)
from talaqi.identity.tokens import AuthTokenKind
from talaqi.platform import ApiError
from talaqi.platform.errors import ErrorEnvelope

router = APIRouter(prefix="/api/v1/auth", tags=["identity"])
_AUTH_FAILURE: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication failed."}
_CSRF_FAILURE: dict[str, Any] = {"model": ErrorEnvelope, "description": "CSRF validation failed."}
_INPUT_FAILURE: dict[str, Any] = {"model": ErrorEnvelope, "description": "Input was rejected."}
_RATE_LIMIT_FAILURE: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "The authentication request rate was exceeded.",
}


def _client(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _limit(request: Request, action: AuthRateLimitAction, identifier: str) -> None:
    limiter: LazyAuthRateLimiter = request.app.state.auth_rate_limits
    await limiter.check(action, client_host=_client(request), identifier=identifier)


def _set_session_cookies(
    response: Response, result: LoginResult | SessionBundle, secure: bool
) -> None:
    access = result.access_cookie
    credentials = result.credentials
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access,
        max_age=ACCESS_LIFETIME_SECONDS,
        path="/",
        httponly=True,
        secure=secure,
        samesite="lax",
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        credentials.refresh_token,
        max_age=REFRESH_LIFETIME_SECONDS,
        path="/",
        httponly=True,
        secure=secure,
        samesite="lax",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        credentials.csrf_secret,
        max_age=REFRESH_LIFETIME_SECONDS,
        path="/",
        httponly=False,
        secure=secure,
        samesite="lax",
    )


def _clear_session_cookies(response: Response, secure: bool) -> None:
    for name, httponly in (
        (ACCESS_COOKIE_NAME, True),
        (REFRESH_COOKIE_NAME, True),
        (CSRF_COOKIE_NAME, False),
    ):
        response.delete_cookie(name, path="/", httponly=httponly, secure=secure, samesite="lax")


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="registerAccount",
    responses={422: _INPUT_FAILURE, 429: _RATE_LIMIT_FAILURE},
)
async def register_account(
    body: RegistrationRequest, request: Request, session: DatabaseSession
) -> RegistrationResponse:
    await _limit(request, AuthRateLimitAction.REGISTER, body.email)
    await build_auth_service(request, session).register(**body.model_dump())
    return RegistrationResponse()


@router.post(
    "/login",
    response_model=AuthenticationResponse,
    operation_id="loginAccount",
    responses={401: _AUTH_FAILURE, 422: _INPUT_FAILURE, 429: _RATE_LIMIT_FAILURE},
)
async def login_account(
    body: LoginRequest, request: Request, response: Response, session: DatabaseSession
) -> AuthenticationResponse:
    await _limit(request, AuthRateLimitAction.LOGIN, body.identifier)
    result = await build_auth_service(request, session).login(body.identifier, body.password)
    _set_session_cookies(response, result, request.app.state.settings_factory().cookie_secure)
    return AuthenticationResponse(email_verified=result.principal.email_verified)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    operation_id="logoutAccount",
    responses={401: _AUTH_FAILURE, 403: _CSRF_FAILURE},
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
    service = build_auth_service(request, session)
    principal = await service.require_access(encoded)
    await service.verify_csrf(
        principal, request.cookies.get(CSRF_COOKIE_NAME), request.headers.get("X-CSRF-Token")
    )
    await service.logout(encoded)
    _clear_session_cookies(response, request.app.state.settings_factory().cookie_secure)
    return LogoutResponse()


async def _recovery_request(
    body: RecoveryRequest,
    request: Request,
    session: DatabaseSession,
    kind: AuthTokenKind,
) -> AcceptedResponse:
    await _limit(request, AuthRateLimitAction.RECOVERY_REQUEST, body.email)
    await build_auth_service(request, session).request_recovery(body.email, kind)
    return AcceptedResponse()


@router.post(
    "/verification/request",
    response_model=AcceptedResponse,
    status_code=202,
    operation_id="requestEmailVerification",
    responses={422: _INPUT_FAILURE, 429: _RATE_LIMIT_FAILURE},
)
async def request_verification(
    body: RecoveryRequest, request: Request, session: DatabaseSession
) -> AcceptedResponse:
    return await _recovery_request(body, request, session, "email_verification")


@router.post(
    "/password-reset/request",
    response_model=AcceptedResponse,
    status_code=202,
    operation_id="requestPasswordReset",
    responses={422: _INPUT_FAILURE, 429: _RATE_LIMIT_FAILURE},
)
async def request_password_reset(
    body: RecoveryRequest, request: Request, session: DatabaseSession
) -> AcceptedResponse:
    return await _recovery_request(body, request, session, "password_reset")


@router.post(
    "/verification/confirm",
    response_model=ConfirmedResponse,
    operation_id="confirmEmailVerification",
    responses={401: _AUTH_FAILURE, 422: _INPUT_FAILURE, 429: _RATE_LIMIT_FAILURE},
)
async def confirm_verification(
    body: RecoveryConfirm, request: Request, session: DatabaseSession
) -> ConfirmedResponse:
    await _limit(request, AuthRateLimitAction.RECOVERY_CONFIRM, body.token)
    await build_auth_service(request, session).confirm_verification(body.token)
    return ConfirmedResponse()


@router.post(
    "/password-reset/confirm",
    response_model=ConfirmedResponse,
    operation_id="confirmPasswordReset",
    responses={
        401: _AUTH_FAILURE,
        403: _CSRF_FAILURE,
        422: _INPUT_FAILURE,
        429: _RATE_LIMIT_FAILURE,
    },
)
async def confirm_password_reset(
    body: PasswordResetConfirm,
    request: Request,
    response: Response,
    session: DatabaseSession,
) -> ConfirmedResponse:
    await _limit(request, AuthRateLimitAction.RECOVERY_CONFIRM, body.token)
    service = build_auth_service(request, session)
    encoded = request.cookies.get(ACCESS_COOKIE_NAME)
    principal = await service.optional_access(encoded)
    if principal is not None:
        await service.verify_csrf(
            principal, request.cookies.get(CSRF_COOKIE_NAME), request.headers.get("X-CSRF-Token")
        )
    await service.confirm_password_reset(body.token, body.new_password)
    _clear_session_cookies(response, request.app.state.settings_factory().cookie_secure)
    return ConfirmedResponse()


@router.post(
    "/refresh",
    response_model=RefreshedResponse,
    operation_id="refreshSession",
    responses={401: _AUTH_FAILURE, 403: _CSRF_FAILURE, 429: _RATE_LIMIT_FAILURE},
)
async def refresh_session(
    request: Request, response: Response, session: DatabaseSession
) -> RefreshedResponse:
    raw = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw is None:
        raise ApiError(
            code="invalid_session", message_key="errors.invalid_session", status_code=401
        )
    await _limit(request, AuthRateLimitAction.REFRESH, raw)
    result = await build_auth_service(request, session).rotate(
        raw, request.cookies.get(CSRF_COOKIE_NAME), request.headers.get("X-CSRF-Token")
    )
    _set_session_cookies(response, result, request.app.state.settings_factory().cookie_secure)
    return RefreshedResponse(email_verified=result.principal.email_verified)


@router.get(
    "/sessions",
    response_model=SessionsResponse,
    operation_id="listSessions",
    responses={401: _AUTH_FAILURE},
)
async def list_sessions(request: Request, session: DatabaseSession) -> SessionsResponse:
    service = build_auth_service(request, session)
    principal = await service.require_user(request)
    records = await service.list_sessions(principal)
    return SessionsResponse(
        sessions=tuple(
            SessionResponse(
                id=record.id,
                current=record.current,
                created_at=record.created_at,
                last_used_at=record.last_used_at,
                expires_at=record.expires_at,
            )
            for record in records
        )
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=RevokedResponse,
    operation_id="revokeSession",
    responses={401: _AUTH_FAILURE, 403: _CSRF_FAILURE, 404: _AUTH_FAILURE},
)
async def revoke_session(
    session_id: UUID, request: Request, response: Response, session: DatabaseSession
) -> RevokedResponse:
    service = build_auth_service(request, session)
    principal = await service.require_user(request)
    await service.verify_csrf(
        principal, request.cookies.get(CSRF_COOKIE_NAME), request.headers.get("X-CSRF-Token")
    )
    if not await service.revoke_owned_session(principal, session_id):
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
    if session_id == principal.session_id:
        _clear_session_cookies(response, request.app.state.settings_factory().cookie_secure)
    return RevokedResponse()


@router.delete(
    "/sessions",
    response_model=RevokedResponse,
    operation_id="revokeAllSessions",
    responses={401: _AUTH_FAILURE, 403: _CSRF_FAILURE},
)
async def revoke_all_sessions(
    request: Request, response: Response, session: DatabaseSession
) -> RevokedResponse:
    service = build_auth_service(request, session)
    principal = await service.require_user(request)
    await service.verify_csrf(
        principal, request.cookies.get(CSRF_COOKIE_NAME), request.headers.get("X-CSRF-Token")
    )
    await service.revoke_all_other(principal)
    _clear_session_cookies(response, request.app.state.settings_factory().cookie_secure)
    return RevokedResponse()
