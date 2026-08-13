from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.outbox.repository import OutboxRepository


class TransactionalEventPublisher:
    """Public infrastructure port that publishes within the caller transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = OutboxRepository(session)

    async def publish(
        self,
        *,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        payload: dict[str, object],
        deduplication_key: str,
        available_at: datetime,
    ) -> None:
        await self._repository.enqueue(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            deduplication_key=deduplication_key,
            available_at=available_at,
        )


__all__ = ["TransactionalEventPublisher"]
