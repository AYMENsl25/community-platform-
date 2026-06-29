from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_authenticated_user
from app.db.session import get_db_session
from app.modules.me.schemas import (
    MyClubSummary,
    MyEventSummary,
    MyNotificationSummary,
    MyPreferences,
    MyPreferencesUpdate,
    MyProfile,
    MyProfileUpdate,
    MyRegistrationSummary,
    MySavedEventSummary,
    NotificationReadState,
    NotificationsReadAllState,
)
from app.modules.me.service import (
    NotificationActionFailedError,
    NotificationNotFoundError,
    ProfileActionFailedError,
    ProfileNotFoundError,
    get_my_clubs,
    get_my_events,
    get_my_notifications,
    get_my_preferences,
    get_my_profile,
    get_my_registrations,
    get_my_saved_events,
    mark_all_my_notifications_read,
    mark_my_notification_read,
    update_my_preferences,
    update_my_profile,
)

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/profile", response_model=MyProfile)
async def get_profile(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> MyProfile:
    try:
        return await get_my_profile(session, current_user)
    except ProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        ) from exc


@router.patch("/profile", response_model=MyProfile)
async def update_profile(
    payload: MyProfileUpdate,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> MyProfile:
    try:
        return await update_my_profile(session, current_user, payload=payload)
    except ProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        ) from exc
    except ProfileActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile update failed",
        ) from exc


@router.get("/preferences", response_model=MyPreferences)
async def get_preferences(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> MyPreferences:
    return await get_my_preferences(session, current_user)


@router.patch("/preferences", response_model=MyPreferences)
async def update_preferences(
    payload: MyPreferencesUpdate,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> MyPreferences:
    try:
        return await update_my_preferences(session, current_user, payload=payload)
    except ProfileActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Preferences update failed",
        ) from exc


@router.get("/clubs", response_model=list[MyClubSummary])
async def list_my_clubs(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> list[MyClubSummary]:
    return await get_my_clubs(session, current_user)


@router.get("/events", response_model=list[MyEventSummary])
async def list_my_events(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> list[MyEventSummary]:
    return await get_my_events(session, current_user)


@router.get("/registrations", response_model=list[MyRegistrationSummary])
async def list_my_registrations(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> list[MyRegistrationSummary]:
    return await get_my_registrations(session, current_user)


@router.get("/saved-events", response_model=list[MySavedEventSummary])
async def list_my_saved_events(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> list[MySavedEventSummary]:
    return await get_my_saved_events(session, current_user)


@router.get("/notifications", response_model=list[MyNotificationSummary])
async def list_my_notifications(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = False,
    session: AsyncSession = Depends(get_db_session),
) -> list[MyNotificationSummary]:
    return await get_my_notifications(
        session,
        current_user,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


@router.patch("/notifications/read-all", response_model=NotificationsReadAllState)
async def mark_all_notifications_read(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> NotificationsReadAllState:
    try:
        return await mark_all_my_notifications_read(session, current_user)
    except NotificationActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Notification update failed",
        ) from exc


@router.patch(
    "/notifications/{notification_id}/read", response_model=NotificationReadState
)
async def mark_notification_read(
    notification_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> NotificationReadState:
    try:
        return await mark_my_notification_read(
            session,
            current_user,
            notification_id=notification_id,
        )
    except NotificationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        ) from exc
    except NotificationActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Notification update failed",
        ) from exc
