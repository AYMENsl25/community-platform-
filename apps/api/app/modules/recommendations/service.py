from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.modules.recommendations.repository import (
    event_exists,
    insert_recommendation_event,
)
from app.modules.recommendations.schemas import (
    RecommendationEventCreate,
    RecommendationEventState,
)


class RecommendationEventNotFoundError(Exception):
    pass


class RecommendationEventActionFailedError(Exception):
    pass


async def track_recommendation_event(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    payload: RecommendationEventCreate,
) -> RecommendationEventState:
    if not await event_exists(session, event_id=payload.event_id):
        raise RecommendationEventNotFoundError

    try:
        state = await insert_recommendation_event(
            session,
            user_id=current_user.id,
            payload=payload,
        )
        await session.commit()
        return state
    except SQLAlchemyError as exc:
        await session.rollback()
        raise RecommendationEventActionFailedError(str(exc)) from exc
