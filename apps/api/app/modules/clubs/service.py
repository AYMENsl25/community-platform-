import re

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.modules.clubs.policies import can_manage_club
from app.modules.clubs.repository import (
    add_club_owner_membership,
    get_club_by_id,
    get_club_by_slug,
    get_club_management_context,
    get_club_viewer_state,
    get_user_club_membership,
    insert_club,
    join_club_for_user,
    leave_club_for_user,
    list_club_member_preview,
    list_club_upcoming_events,
    list_public_clubs,
    soft_delete_club_by_id,
    update_club_by_id,
)
from app.modules.clubs.schemas import (
    ClubCard,
    ClubCreate,
    ClubDeletionState,
    ClubDetail,
    ClubEventSummary,
    ClubMemberPreview,
    ClubMembershipState,
    ClubUpdate,
    ClubViewerState,
)


class ClubNotFoundError(Exception):
    pass


class ClubMembershipNotFoundError(Exception):
    pass


class ClubForbiddenError(Exception):
    pass


class ClubActionFailedError(Exception):
    pass


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "club"


def can_manage_club_from_context(
    current_user: CurrentUser,
    context: dict[str, str | None],
) -> bool:
    return can_manage_club(
        current_user,
        owner_id=str(context["owner_id"]),
        member_role=context.get("member_role"),
        member_status=context.get("member_status"),
    )


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


async def get_club_members(
    session: AsyncSession,
    *,
    club_id: str,
    limit: int,
) -> list[ClubMemberPreview]:
    if await get_club_by_id(session, club_id) is None:
        raise ClubNotFoundError
    return await list_club_member_preview(session, club_id=club_id, limit=limit)


async def get_club_events(
    session: AsyncSession,
    *,
    club_id: str,
    limit: int,
) -> list[ClubEventSummary]:
    if await get_club_by_id(session, club_id) is None:
        raise ClubNotFoundError
    return await list_club_upcoming_events(session, club_id=club_id, limit=limit)


async def get_my_club_membership_state(
    session: AsyncSession,
    *,
    club_id: str,
    current_user: CurrentUser,
) -> ClubViewerState:
    if await get_club_by_id(session, club_id) is None:
        raise ClubNotFoundError
    return await get_club_viewer_state(
        session,
        club_id=club_id,
        user_id=current_user.id,
    )


async def create_club_action(
    session: AsyncSession,
    *,
    payload: ClubCreate,
    current_user: CurrentUser,
) -> ClubDetail:
    slug = payload.slug or slugify(payload.name)
    try:
        club_id = await insert_club(
            session,
            payload=payload,
            owner_id=current_user.id,
            slug=slug,
        )
        await add_club_owner_membership(
            session,
            club_id=club_id,
            owner_id=current_user.id,
        )
        club = await get_club_by_id(session, club_id)
        if club is None:
            raise ClubNotFoundError
        await session.commit()
        return club
    except ClubNotFoundError:
        await session.rollback()
        raise
    except SQLAlchemyError as exc:
        await session.rollback()
        raise ClubActionFailedError(str(exc)) from exc


async def update_club_action(
    session: AsyncSession,
    *,
    club_id: str,
    payload: ClubUpdate,
    current_user: CurrentUser,
) -> ClubDetail:
    context = await get_club_management_context(
        session, club_id=club_id, user_id=current_user.id
    )
    if context is None:
        raise ClubNotFoundError
    if not can_manage_club_from_context(current_user, context):
        raise ClubForbiddenError

    try:
        await update_club_by_id(session, club_id=club_id, payload=payload)
        club = await get_club_by_id(session, club_id)
        if club is None:
            raise ClubNotFoundError
        await session.commit()
        return club
    except ClubNotFoundError:
        await session.rollback()
        raise
    except SQLAlchemyError as exc:
        await session.rollback()
        raise ClubActionFailedError(str(exc)) from exc


async def delete_club_action(
    session: AsyncSession,
    *,
    club_id: str,
    current_user: CurrentUser,
) -> ClubDeletionState:
    context = await get_club_management_context(
        session, club_id=club_id, user_id=current_user.id
    )
    if context is None:
        raise ClubNotFoundError
    if not can_manage_club_from_context(current_user, context):
        raise ClubForbiddenError

    try:
        await soft_delete_club_by_id(session, club_id=club_id)
        await session.commit()
        return ClubDeletionState(club_id=club_id, deleted=True)
    except SQLAlchemyError as exc:
        await session.rollback()
        raise ClubActionFailedError(str(exc)) from exc


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
