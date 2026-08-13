from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from talaqi.communications.service import (
    SUPPORTED_NOTIFICATION_EVENTS,
    NotificationProjectionHandler,
)

from talaqi_worker.outbox import TransactionalOutboxWorker


def build_notification_worker(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    worker_id: str,
    lease_duration: timedelta = timedelta(seconds=30),
) -> TransactionalOutboxWorker:
    handler = NotificationProjectionHandler(session_factory)
    return TransactionalOutboxWorker(
        session_factory,
        dict.fromkeys(SUPPORTED_NOTIFICATION_EVENTS, handler),
        worker_id=worker_id,
        lease_duration=lease_duration,
    )


__all__ = ["build_notification_worker"]
