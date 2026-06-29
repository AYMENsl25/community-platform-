from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.modules.clubs.repository import (
    get_club_by_id,
    get_club_by_slug,
    get_user_club_membership,
    join_club_for_user,
    leave_club_for_user,
    list_public_clubs,
)
from app.modules.clubs.schemas import ClubCard, ClubDetail, ClubMembershipState


class ClubNotFoundError(Exception):
    pass


class ClubMembershipNotFoundError(Exception):
    pass


class ClubActionFailedError(Exception):
    pass


async def list_clubs(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    city: str | None = None,
    q: str | None = None,
) -> list[ClubCard]:
    return await list_public_clubs(session, limit=limit, offset=offset, city=city, q=q)


async def get_club_detail(session: AsyncSession, slug: str) -> ClubDetail | None:
    return await get_club_by_slug(session, slug)


async def join_club_action(
    session: AsyncSession,
    *,
    club_id: str,
    current_user: CurrentUser,
) -> ClubMembershipState:
    if await get_club_by_id(session, club_id) is None:
        raise ClubNotFoundError

    try:
        membership = await join_club_for_user(
            session, user_id=current_user.id, club_id=club_id
        )
        await session.commit()
        return membership
    except SQLAlchemyError as exc:
        await session.rollback()
        raise ClubActionFailedError(str(exc)) from exc


async def leave_club_action(
    session: AsyncSession,
    *,
    club_id: str,
    current_user: CurrentUser,
) -> ClubMembershipState:
    if await get_club_by_id(session, club_id) is None:
        raise ClubNotFoundError

    try:
        await leave_club_for_user(session, user_id=current_user.id, club_id=club_id)
        membership = await get_user_club_membership(
            session, user_id=current_user.id, club_id=club_id
        )
        if membership is None:
            raise ClubMembershipNotFoundError
        await session.commit()
        return membership
    except ClubMembershipNotFoundError:
        await session.rollback()
        raise
    except SQLAlchemyError as exc:
        await session.rollback()
        raise ClubActionFailedError(str(exc)) from exc
