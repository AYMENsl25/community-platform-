from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_authenticated_user
from app.db.session import get_db_session
from app.modules.recommendations.schemas import (
    RecommendationEventCreate,
    RecommendationEventState,
)
from app.modules.recommendations.service import (
    RecommendationEventActionFailedError,
    RecommendationEventNotFoundError,
    track_recommendation_event,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post(
    "/events",
    response_model=RecommendationEventState,
    status_code=status.HTTP_201_CREATED,
)
async def track_event_recommendation(
    payload: RecommendationEventCreate,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> RecommendationEventState:
    try:
        return await track_recommendation_event(
            session,
            current_user=current_user,
            payload=payload,
        )
    except RecommendationEventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    except RecommendationEventActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recommendation event tracking failed",
        ) from exc
