from __future__ import annotations

import hmac
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from talaqi.db.identifiers import generate_uuid7
from talaqi.identity.csrf import CsrfService
from talaqi.identity.models import (
    AuthPrincipal,
    LoginResult,
    NewAuthToken,
    NewSession,
    NewUser,
    RegistrationResult,
    SessionBundle,
    SessionCredentials,
    SessionSummary,
    UserRecord,
)
from talaqi.identity.passwords import PasswordService, normalize_email, normalize_login_identifier
from talaqi.identity.repository import IdentityRepositoryProtocol
from talaqi.identity.sessions import (
    ACCESS_COOKIE_NAME,
    AccessSessionCodec,
    AccessToken,
    RefreshTokenCodec,
)
from talaqi.identity.tokens import AuthTokenCodec, AuthTokenKind, invalid_recovery_token
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
        session_secret: str,
    ) -> None:
        self.repository = repository
        self.passwords = passwords
        self.codec = codec
        self._terms_version = current_terms_version
        self._privacy_version = current_privacy_version
        self.refresh_tokens = RefreshTokenCodec(session_secret)
        self.csrf = CsrfService(session_secret)
        self.auth_tokens = AuthTokenCodec(session_secret)

    def _credentials(self) -> SessionCredentials:
        refresh = self.refresh_tokens.issue()
        csrf = self.csrf.issue()
        return SessionCredentials(
            refresh, csrf, self.refresh_tokens.hash(refresh), self.csrf.hash(csrf)
        )

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
        credentials = self._credentials()
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
        await self.repository.touch_session(token.session_id, user.id, current)
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

    async def optional_access(
        self, encoded: str | None, *, now: datetime | None = None
    ) -> AuthPrincipal | None:
        if encoded is None:
            return None
        try:
            return await self.require_access(encoded, now=now)
        except ApiError:
            return None

    async def logout(self, encoded: str, *, now: datetime | None = None) -> None:
        current = now or datetime.now(UTC)
        principal = await self.require_access(encoded, now=current)
        await self.repository.revoke_session(principal.session_id, "logout", current)

    async def request_recovery(
        self,
        email: str,
        kind: AuthTokenKind,
        *,
        locale_hint: str = "en",
        now: datetime | None = None,
    ) -> RegistrationResult:
        current = now or datetime.now(UTC)
        try:
            normalized = normalize_email(email)
        except ApiError:
            return RegistrationResult()
        user = await self.repository.find_user_by_email(normalized)
        if user is None or user.status != "active":
            return RegistrationResult()
        token_id = uuid4()
        public = self.auth_tokens.public_token(token_id, kind)
        await self.repository.create_auth_token(
            NewAuthToken(
                token_id,
                user.id,
                kind,
                self.auth_tokens.stored_hash(public, kind),
                self.auth_tokens.expiry(kind, current),
            ),
            locale_hint,
        )
        return RegistrationResult()

    async def confirm_verification(self, public_token: str, *, now: datetime | None = None) -> None:
        current = now or datetime.now(UTC)
        user = await self._consume_recovery_token(public_token, "email_verification", current)
        await self.repository.mark_email_verified(user.id, current)

    async def confirm_password_reset(
        self, public_token: str, new_password: str, *, now: datetime | None = None
    ) -> None:
        current = now or datetime.now(UTC)
        user = await self._consume_recovery_token(public_token, "password_reset", current)
        encoded = await self.passwords.hash(new_password)
        await self.repository.replace_password(user.id, encoded)
        await self.repository.revoke_all_sessions(user.id, "password_reset", current)

    async def _consume_recovery_token(
        self, public_token: str, kind: AuthTokenKind, now: datetime
    ) -> UserRecord:
        token_id = self.auth_tokens.verify(public_token, kind)
        found = await self.repository.lock_auth_token(token_id)
        if found is None:
            raise invalid_recovery_token()
        record, user = found
        expected = self.auth_tokens.stored_hash(public_token, kind)
        stored_matches = hmac.compare_digest(record.token_hash, expected)
        if (
            record.kind != kind
            or record.used_at is not None
            or record.expires_at.utcoffset() is None
            or record.expires_at <= now
            or user.status != "active"
            or not stored_matches
        ):
            raise invalid_recovery_token()
        await self.repository.mark_auth_token_used(record.id, now)
        return user

    async def rotate(
        self,
        refresh_token: str,
        csrf_cookie: str | None,
        csrf_header: str | None,
        *,
        now: datetime | None = None,
    ) -> SessionBundle:
        current = now or datetime.now(UTC)
        found = await self.repository.find_refresh_session_for_update(
            self.refresh_tokens.hash(refresh_token)
        )
        if found is None:
            raise _invalid_credentials()
        session, user = found
        self.csrf.verify(csrf_cookie, csrf_header, session.csrf_secret_hash)
        if session.revoked_at is not None:
            if session.rotated_at is not None:
                await self.repository.persist_replay_revocation(session.family_id, current)
            raise _invalid_credentials()
        if session.expires_at <= current or user.status != "active":
            raise _invalid_credentials()
        credentials = self._credentials()
        replacement_id = generate_uuid7()
        replacement = NewSession(
            replacement_id,
            user.id,
            session.family_id,
            credentials.refresh_token_hash(),
            credentials.csrf_secret_hash(),
            self.refresh_tokens.expiry(current),
        )
        await self.repository.rotate_session(session, replacement, current)
        principal = AuthPrincipal(
            user.id,
            replacement_id,
            user.email_verified_at is not None,
            user.status,
            user.is_platform_admin,
        )
        return SessionBundle(
            principal,
            self.codec.encode(AccessToken(replacement_id, user.id, current)),
            credentials,
        )

    async def list_sessions(self, principal: AuthPrincipal) -> tuple[SessionSummary, ...]:
        return await self.repository.list_sessions(principal.user_id, principal.session_id)

    async def revoke_owned_session(
        self, principal: AuthPrincipal, session_id: UUID, *, now: datetime | None = None
    ) -> bool:
        return await self.repository.revoke_owned_session(
            principal.user_id, session_id, "user_revoked", now or datetime.now(UTC)
        )

    async def revoke_all_other(
        self, principal: AuthPrincipal, *, now: datetime | None = None
    ) -> None:
        # Revoking all includes the current session by the public contract.
        await self.repository.revoke_all_sessions(
            principal.user_id, "user_revoked_all", now or datetime.now(UTC)
        )

    async def verify_csrf(
        self,
        principal: AuthPrincipal,
        cookie: str | None,
        header: str | None,
        *,
        now: datetime | None = None,
    ) -> None:
        found = await self.repository.find_active_session(
            principal.session_id, now or datetime.now(UTC)
        )
        if found is None or found[1].id != principal.user_id:
            raise _invalid_credentials()
        self.csrf.verify(cookie, header, found[0].csrf_secret_hash)
