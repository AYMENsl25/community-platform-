from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.config import Settings
from talaqi.identity.models import AuthPrincipal
from talaqi.identity.passwords import PasswordPolicy, PasswordService
from talaqi.identity.repository import IdentityRepository
from talaqi.identity.service import AuthService
from talaqi.identity.sessions import AccessSessionCodec
from talaqi.runtime import get_db_session

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session, scope="function")]


def build_auth_service(request: Request, session: AsyncSession) -> AuthService:
    settings: Settings = request.app.state.settings_factory()
    return AuthService(
        IdentityRepository(session),
        PasswordService(PasswordPolicy.from_package_resource()),
        AccessSessionCodec(settings.session_secret.get_secret_value()),
        current_terms_version=settings.current_terms_version,
        current_privacy_version=settings.current_privacy_version,
    )


async def require_user(request: Request, session: DatabaseSession) -> AuthPrincipal:
    return await build_auth_service(request, session).require_user(request)


CurrentPrincipal = Annotated[AuthPrincipal, Depends(require_user)]
