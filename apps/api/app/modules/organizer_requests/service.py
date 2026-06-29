from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.modules.organizer_requests.repository import (
    get_user_organizer_request,
    list_organizer_requests,
    review_organizer_request,
    upsert_user_organizer_request,
)
from app.modules.organizer_requests.schemas import (
    OrganizerRequestCreate,
    OrganizerRequestReview,
    OrganizerRequestState,
)


class AdminRequiredError(Exception):
    pass


class OrganizerRequestNotFoundError(Exception):
    pass


class OrganizerRequestActionFailedError(Exception):
    pass


def require_admin(current_user: CurrentUser) -> None:
    if current_user.platform_role != "admin":
        raise AdminRequiredError


async def get_my_organizer_request(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
) -> OrganizerRequestState | None:
    return await get_user_organizer_request(session, user_id=current_user.id)


async def submit_my_organizer_request(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    payload: OrganizerRequestCreate,
) -> OrganizerRequestState:
    try:
        request = await upsert_user_organizer_request(
            session,
            user_id=current_user.id,
            payload=payload,
        )
        await session.commit()
        return request
    except SQLAlchemyError as exc:
        await session.rollback()
        raise OrganizerRequestActionFailedError(str(exc)) from exc


async def list_admin_organizer_requests(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    status_filter: str | None,
    limit: int,
    offset: int,
) -> list[OrganizerRequestState]:
    require_admin(current_user)
    return await list_organizer_requests(
        session,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


async def review_admin_organizer_request(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    request_id: str,
    review_status: str,
    payload: OrganizerRequestReview,
) -> OrganizerRequestState:
    require_admin(current_user)
    try:
        request = await review_organizer_request(
            session,
            request_id=request_id,
            reviewer_id=current_user.id,
            status=review_status,
            payload=payload,
        )
        if request is None:
            raise OrganizerRequestNotFoundError
        await session.commit()
        return request
    except OrganizerRequestNotFoundError:
        await session.rollback()
        raise
    except SQLAlchemyError as exc:
        await session.rollback()
        raise OrganizerRequestActionFailedError(str(exc)) from exc
