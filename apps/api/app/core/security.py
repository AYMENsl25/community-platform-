from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient, PyJWKClientError, PyJWTError
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
    display_name: str | None = None
    avatar_url: str | None = None


@dataclass(frozen=True)
class ClerkIdentity:
    clerk_user_id: str
    email: str
    display_name: str
    avatar_url: str | None = None


@lru_cache(maxsize=8)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def validate_authorized_party(
    payload: dict[str, Any], authorized_parties: list[str]
) -> None:
    authorized_party = payload.get("azp")
    if (
        authorized_party
        and authorized_parties
        and authorized_party not in authorized_parties
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token authorized party.",
        )


def extract_clerk_identity(payload: dict[str, Any]) -> ClerkIdentity:
    clerk_user_id = str(payload.get("sub") or "").strip()
    email = str(
        payload.get("email")
        or payload.get("primary_email_address")
        or payload.get("email_address")
        or ""
    ).strip()
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is missing subject."
        )
    if not email:
        email = f"{clerk_user_id}@clerk.local"

    display_name = str(
        payload.get("name")
        or payload.get("full_name")
        or payload.get("username")
        or email.split("@", maxsplit=1)[0]
    ).strip()
    if len(display_name) < 2:
        display_name = "COMMUNITI Member"

    avatar_url = (
        payload.get("image_url") or payload.get("picture") or payload.get("avatar_url")
    )
    return ClerkIdentity(
        clerk_user_id=clerk_user_id,
        email=email,
        display_name=display_name[:120],
        avatar_url=str(avatar_url) if avatar_url else None,
    )


def decode_clerk_jwt(token: str) -> dict[str, Any]:
    jwks_url = settings.effective_clerk_jwks_url
    if not settings.clerk_issuer or not jwks_url:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Clerk authentication is not configured.",
        )

    try:
        signing_key = get_jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.clerk_audience,
            issuer=settings.clerk_issuer,
            options={"verify_aud": settings.clerk_audience is not None},
        )
    except (PyJWKClientError, PyJWTError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token."
        ) from exc

    validate_authorized_party(payload, settings.clerk_authorized_party_list)
    return payload


async def get_current_user_by_email(
    session: AsyncSession, email: str
) -> CurrentUser | None:
    result = await session.execute(
        text(
            """
            SELECT
              id::text AS id,
              clerk_user_id,
              email,
              platform_role::text AS platform_role,
              display_name,
              avatar_url
            FROM users
            WHERE email = :email
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"email": email},
    )
    row = result.first()
    return CurrentUser(**row._mapping) if row else None


async def upsert_current_user_from_clerk(
    session: AsyncSession, identity: ClerkIdentity
) -> CurrentUser:
    existing = await session.execute(
        text(
            """
            SELECT id
            FROM users
            WHERE clerk_user_id = :clerk_user_id
               OR email = :email
            LIMIT 1
            """
        ),
        {"clerk_user_id": identity.clerk_user_id, "email": identity.email},
    )
    row = existing.first()
    if row:
        user_id = row._mapping["id"]
        result = await session.execute(
            text(
                """
                UPDATE users
                SET clerk_user_id = :clerk_user_id,
                    email = :email,
                    display_name = :display_name,
                    avatar_url = :avatar_url,
                    updated_at = now(),
                    deleted_at = NULL
                WHERE id = :user_id
                RETURNING
                  id::text AS id,
                  clerk_user_id,
                  email,
                  platform_role::text AS platform_role,
                  display_name,
                  avatar_url
                """
            ),
            {
                "user_id": user_id,
                "clerk_user_id": identity.clerk_user_id,
                "email": identity.email,
                "display_name": identity.display_name,
                "avatar_url": identity.avatar_url,
            },
        )
    else:
        result = await session.execute(
            text(
                """
                INSERT INTO users (
                  clerk_user_id,
                  email,
                  display_name,
                  avatar_url,
                  is_onboarded
                )
                VALUES (
                  :clerk_user_id,
                  :email,
                  :display_name,
                  :avatar_url,
                  false
                )
                RETURNING
                  id::text AS id,
                  clerk_user_id,
                  email,
                  platform_role::text AS platform_role,
                  display_name,
                  avatar_url
                """
            ),
            {
                "clerk_user_id": identity.clerk_user_id,
                "email": identity.email,
                "display_name": identity.display_name,
                "avatar_url": identity.avatar_url,
            },
        )

    await session.commit()
    user_row = result.one()
    return CurrentUser(**user_row._mapping)


async def require_authenticated_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
    x_communiti_user_email: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    token = extract_bearer_token(authorization)
    if token:
        identity = extract_clerk_identity(decode_clerk_jwt(token))
        return await upsert_current_user_from_clerk(session, identity)

    if settings.environment == "development":
        email = x_communiti_user_email or "member@communiti.local"
        current_user = await get_current_user_by_email(session, email)
        if current_user:
            return current_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
    )
