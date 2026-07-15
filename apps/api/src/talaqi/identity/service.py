from __future__ import annotations

import secrets
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Protocol

from talaqi.db.identifiers import generate_uuid7
from talaqi.identity.models import (
    AuthPrincipal,
    LoginResult,
    NewSession,
    NewUser,
    RegistrationResult,
    SessionCredentials,
)
from talaqi.identity.passwords import PasswordService, normalize_email, normalize_login_identifier
from talaqi.identity.repository import IdentityRepositoryProtocol
from talaqi.identity.sessions import ACCESS_COOKIE_NAME, AccessSessionCodec, AccessToken
from talaqi.platform import ApiError

_DUMMY_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$Lpm/Lp7Pi4/BGiV5tCGoQg$"
    "yBSqOu3Mu/QL0TgL8EngAUcK6oI8W0ln7GNcBBaYHnE"  # pragma: allowlist secret
)


def _invalid_credentials() -> ApiError:
    return ApiError(
        code="invalid_credentials", message_key="errors.invalid_credentials", status_code=401
    )


class AuthRequest(Protocol):
    @property
    def cookies(self) -> Mapping[str, str]: ...


class AuthService:
    def __init__(
        self,
        repository: IdentityRepositoryProtocol,
        passwords: PasswordService,
        codec: AccessSessionCodec,
        *,
        current_terms_version: str,
        current_privacy_version: str,
    ) -> None:
        self.repository = repository
        self.passwords = passwords
        self.codec = codec
        self._terms_version = current_terms_version
        self._privacy_version = current_privacy_version

    async def register(
        self,
        *,
        email: str,
        password: str,
        age_attested: bool,
        terms_version: str,
        privacy_version: str,
    ) -> RegistrationResult:
        if (
            not age_attested
            or terms_version != self._terms_version
            or privacy_version != self._privacy_version
        ):
            raise ApiError(
                code="legal_acceptance_required",
                message_key="errors.legal_acceptance_required",
                status_code=422,
            )
        normalized = normalize_email(email)
        encoded = await self.passwords.hash(password)
        await self.repository.create_user(
            NewUser(
                id=generate_uuid7(),
                email=normalized,
                password_hash=encoded,
                terms_version=terms_version,
                privacy_version=privacy_version,
                age_attested_at=datetime.now(UTC),
            )
        )
        return RegistrationResult()

    async def login(
        self, identifier: str, password: str, *, now: datetime | None = None
    ) -> LoginResult:
        current = now or datetime.now(UTC)
        normalized = normalize_login_identifier(identifier)
        user = await self.repository.find_for_login(normalized) if normalized is not None else None
        encoded = user.password_hash if user is not None else _DUMMY_HASH
        verified = await self.passwords.verify(encoded, password)
        if user is None:
            raise _invalid_credentials()
        unavailable = user.status != "active" or (
            user.locked_until is not None and user.locked_until > current
        )
        if unavailable or not verified:
            if user.status == "active" and not unavailable:
                await self.repository.record_failed_login(user.id, current)
            raise _invalid_credentials()
        await self.repository.clear_failed_login(user.id)
        session_id = generate_uuid7()
        credentials = SessionCredentials(
            refresh_token=secrets.token_bytes(32),
            csrf_secret=secrets.token_bytes(32),
        )
        session = await self.repository.create_session(
            NewSession(
                id=session_id,
                user_id=user.id,
                family_id=generate_uuid7(),
                refresh_token_hash=credentials.refresh_token_hash(),
                csrf_secret_hash=credentials.csrf_secret_hash(),
                expires_at=current + timedelta(days=30),
            )
        )
        principal = AuthPrincipal(
            user_id=user.id,
            session_id=session.id,
            email_verified=user.email_verified_at is not None,
            status=user.status,
            is_platform_admin=user.is_platform_admin,
        )
        cookie = self.codec.encode(AccessToken(session.id, user.id, current))
        return LoginResult(principal, cookie, credentials)

    async def require_access(self, encoded: str, *, now: datetime | None = None) -> AuthPrincipal:
        current = now or datetime.now(UTC)
        try:
            token = self.codec.decode(encoded, now=current)
        except ApiError:
            raise _invalid_credentials() from None
        found = await self.repository.find_active_session(token.session_id, current)
        if found is None:
            raise _invalid_credentials()
        _session, user = found
        if user.id != token.user_id or user.status != "active":
            raise _invalid_credentials()
        return AuthPrincipal(
            user.id,
            token.session_id,
            user.email_verified_at is not None,
            user.status,
            user.is_platform_admin,
        )

    async def require_user(
        self, request: AuthRequest, *, now: datetime | None = None
    ) -> AuthPrincipal:
        encoded = request.cookies.get(ACCESS_COOKIE_NAME)
        if encoded is None:
            raise ApiError(
                code="authentication_required",
                message_key="errors.authentication_required",
                status_code=401,
            )
        return await self.require_access(encoded, now=now)

    async def logout(self, encoded: str, *, now: datetime | None = None) -> None:
        current = now or datetime.now(UTC)
        principal = await self.require_access(encoded, now=current)
        await self.repository.revoke_session(principal.session_id, "logout", current)
