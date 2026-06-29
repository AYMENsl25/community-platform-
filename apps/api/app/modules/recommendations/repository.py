from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recommendations.schemas import (
    RecommendationEventCreate,
    RecommendationEventState,
)


async def event_exists(session: AsyncSession, *, event_id: str) -> bool:
    result = await session.execute(
        text(
            """
            SELECT 1
            FROM events
            WHERE id = CAST(:event_id AS uuid)
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"event_id": event_id},
    )
    return result.first() is not None


async def insert_recommendation_event(
    session: AsyncSession,
    *,
    user_id: str,
    payload: RecommendationEventCreate,
) -> RecommendationEventState:
    result = await session.execute(
        text(
            """
            INSERT INTO recommendation_events (user_id, event_id, source, score, action)
            VALUES (
              CAST(:user_id AS uuid),
              CAST(:event_id AS uuid),
              :source,
              :score,
              CAST(:action AS recommendation_action)
            )
            RETURNING
              id::text AS id,
              user_id::text AS user_id,
              event_id::text AS event_id,
              source,
              score,
              action::text AS action,
              created_at
            """
        ),
        {"user_id": user_id, **payload.model_dump()},
    )
    return RecommendationEventState.model_validate(result.one()._mapping)
