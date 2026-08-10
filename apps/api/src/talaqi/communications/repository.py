from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.communications.models import Notification, NotificationPreferences
from talaqi.outbox import OutboxEvent


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def project(
        self,
        event: OutboxEvent,
        *,
        recipient_user_id: UUID,
        category: str,
        title_key: str,
        body_key: str,
        parameters: Mapping[str, object],
        action_path: str | None,
        source_type: str | None,
        source_id: UUID | None,
    ) -> bool:
        preferences = await self.preferences(recipient_user_id)
        if preferences is None:
            return False
        statement = text(
            """
            INSERT INTO talaqi.notifications (
                recipient_user_id, type_key, title_key, body_key, parameters,
                action_path, source_type, source_id, outbox_event_id
            ) VALUES (
                :recipient_user_id, :type_key, :title_key, :body_key, :parameters,
                :action_path, :source_type, :source_id, :outbox_event_id
            )
            ON CONFLICT (outbox_event_id) WHERE outbox_event_id IS NOT NULL DO NOTHING
            RETURNING id
            """
        ).bindparams(bindparam("parameters", type_=JSONB))
        notification_id = await self._session.scalar(
            statement,
            {
                "recipient_user_id": recipient_user_id,
                "type_key": event.event_type,
                "title_key": title_key,
                "body_key": body_key,
                "parameters": dict(parameters),
                "action_path": action_path,
                "source_type": source_type,
                "source_id": source_id,
                "outbox_event_id": event.id,
            },
        )
        if notification_id is None:
            return False
        await self._session.execute(
            text(
                """
                INSERT INTO talaqi.notification_deliveries (
                    notification_id, channel, status, delivered_at
                ) VALUES (
                    :notification_id, 'in_app', 'delivered', clock_timestamp()
                )
                """
            ),
            {"notification_id": notification_id},
        )
        email_allowed = (
            preferences.security_email
            if category == "security"
            else preferences.event_email
            if category == "event"
            else preferences.community_email
        )
        if email_allowed:
            await self._session.execute(
                text(
                    """
                    INSERT INTO talaqi.notification_deliveries (notification_id, channel)
                    VALUES (:notification_id, 'email')
                    """
                ),
                {"notification_id": notification_id},
            )
        return True

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        after: tuple[datetime, UUID] | None,
    ) -> tuple[Notification, ...]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id, type_key, title_key, body_key, parameters, action_path,
                               source_type, source_id, read_at, created_at
                        FROM talaqi.notifications
                        WHERE recipient_user_id = :user_id
                          AND (CAST(:after_created_at AS timestamptz) IS NULL
                               OR (created_at, id) < (
                                   CAST(:after_created_at AS timestamptz),
                                   CAST(:after_id AS uuid)
                               ))
                        ORDER BY created_at DESC, id DESC
                        LIMIT :limit
                        """
                    ),
                    {
                        "user_id": user_id,
                        "after_created_at": after[0] if after else None,
                        "after_id": after[1] if after else None,
                        "limit": limit,
                    },
                )
            )
            .mappings()
            .all()
        )
        return tuple(self._notification(cast(Mapping[str, object], row)) for row in rows)

    async def unread_count(self, user_id: UUID) -> int:
        value = await self._session.scalar(
            text(
                "SELECT count(*) FROM talaqi.notifications "
                "WHERE recipient_user_id = :user_id AND read_at IS NULL"
            ),
            {"user_id": user_id},
        )
        return int(value or 0)

    async def get_for_user(self, user_id: UUID, notification_id: UUID) -> Notification | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id, type_key, title_key, body_key, parameters, action_path,
                               source_type, source_id, read_at, created_at
                        FROM talaqi.notifications
                        WHERE id = :notification_id AND recipient_user_id = :user_id
                        """
                    ),
                    {"notification_id": notification_id, "user_id": user_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else self._notification(cast(Mapping[str, object], row))

    async def mark_read(self, user_id: UUID, notification_id: UUID, *, now: datetime) -> bool:
        value = await self._session.scalar(
            text(
                """
                UPDATE talaqi.notifications SET read_at = COALESCE(read_at, :now)
                WHERE id = :notification_id AND recipient_user_id = :user_id
                RETURNING id
                """
            ),
            {"notification_id": notification_id, "user_id": user_id, "now": now},
        )
        return value is not None

    async def mark_all_read(self, user_id: UUID, *, now: datetime) -> int:
        values = (
            (
                await self._session.execute(
                    text(
                        """
                    UPDATE talaqi.notifications SET read_at = :now
                    WHERE recipient_user_id = :user_id AND read_at IS NULL
                    RETURNING id
                    """
                    ),
                    {"user_id": user_id, "now": now},
                )
            )
            .scalars()
            .all()
        )
        return len(values)

    async def preferences(self, user_id: UUID) -> NotificationPreferences | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT
                            COALESCE(profile.notify_event_email, true) AS notify_event_email,
                            COALESCE(profile.notify_community_email, true) AS notify_community_email
                        FROM talaqi.users AS user_account
                        LEFT JOIN talaqi.profiles AS profile
                          ON profile.user_id = user_account.id
                        WHERE user_account.id = :user_id
                        """
                    ),
                    {"user_id": user_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return NotificationPreferences(
            security_email=True,
            event_email=cast(bool, row["notify_event_email"]),
            community_email=cast(bool, row["notify_community_email"]),
        )

    async def update_preferences(
        self, user_id: UUID, *, event_email: bool, community_email: bool
    ) -> NotificationPreferences | None:
        updated = await self._session.scalar(
            text(
                """
                UPDATE talaqi.profiles
                SET notify_security_email = true,
                    notify_event_email = :event_email,
                    notify_community_email = :community_email
                WHERE user_id = :user_id
                RETURNING user_id
                """
            ),
            {
                "user_id": user_id,
                "event_email": event_email,
                "community_email": community_email,
            },
        )
        return None if updated is None else await self.preferences(user_id)

    @staticmethod
    def _notification(row: Mapping[str, object]) -> Notification:
        return Notification(
            id=cast(UUID, row["id"]),
            type_key=cast(str, row["type_key"]),
            title_key=cast(str, row["title_key"]),
            body_key=cast(str, row["body_key"]),
            parameters=cast(dict[str, object], row["parameters"]),
            action_path=cast(str | None, row["action_path"]),
            source_type=cast(str | None, row["source_type"]),
            source_id=cast(UUID | None, row["source_id"]),
            read_at=cast(datetime | None, row["read_at"]),
            created_at=cast(datetime, row["created_at"]),
        )


__all__ = ["NotificationRepository"]
