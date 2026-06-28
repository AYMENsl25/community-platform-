from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session


@dataclass(frozen=True)
class CurrentUser:
    id: str
    clerk_user_id: str
    email: str
    platform_role: str = "user"


async def require_authenticated_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_communiti_user_email: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if settings.environment != "development" and not settings.clerk_issuer:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Clerk authentication is not configured.",
        )

    email = x_communiti_user_email or "member@communiti.local"
    result = await session.execute(
        text(
            """
            SELECT
              id::text AS id,
              clerk_user_id,
              email,
              platform_role::text AS platform_role
            FROM users
            WHERE email = :email
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"email": email},
    )
    row = result.first()
    if row:
        return CurrentUser(**row._mapping)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authenticated user was not found in the local database.",
    )
