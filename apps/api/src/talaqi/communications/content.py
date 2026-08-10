from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.db.identifiers import generate_uuid7
from talaqi.outbox import TransactionalEventPublisher
from talaqi.platform import ApiError

ClubAudience = Literal["all_members", "admins"]
EventAudience = Literal["all_active", "confirmed", "cash_pending", "waitlisted"]


@dataclass(frozen=True, slots=True)
class PublishedContent:
    id: UUID
    title: str
    body: str
    audience_key: str
    published_at: datetime


class OrganizerContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_club_announcement(
        self,
        *,
        club_id: UUID,
        author_user_id: UUID,
        title: str,
        body: str,
        audience: ClubAudience,
        deduplication_key: str,
        now: datetime,
    ) -> PublishedContent:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        INSERT INTO talaqi.announcements (
                            id, club_id, author_user_id, title, body, audience_key,
                            deduplication_key, published_at
                        ) VALUES (
                            :id, :club_id, :author_user_id, :title, :body, :audience,
                            :deduplication_key, :now
                        )
                        ON CONFLICT (deduplication_key) DO UPDATE
                        SET deduplication_key = talaqi.announcements.deduplication_key
                        RETURNING id, club_id, author_user_id, title, body,
                                  audience_key, published_at
                        """
                    ),
                    {
                        "id": generate_uuid7(),
                        "club_id": club_id,
                        "author_user_id": author_user_id,
                        "title": title,
                        "body": body,
                        "audience": audience,
                        "deduplication_key": deduplication_key,
                        "now": now,
                    },
                )
            )
            .mappings()
            .one()
        )
        if (
            row["club_id"] != club_id
            or row["author_user_id"] != author_user_id
            or row["title"] != title
            or row["body"] != body
            or row["audience_key"] != audience
        ):
            raise ApiError(
                code="idempotency_conflict", message_key="errors.conflict", status_code=409
            )
        item = _content(row)
        recipients = await self._club_recipients(club_id, audience)
        await self._snapshot_recipients("announcement", item.id, recipients)
        await self._publish_recipients(
            recipients,
            aggregate_type="announcement",
            aggregate_id=item.id,
            event_type="club.announcement_published",
            payload={"club_id": str(club_id), "announcement_id": str(item.id)},
            now=item.published_at,
        )
        return item

    async def create_event_update(
        self,
        *,
        event_id: UUID,
        author_user_id: UUID,
        title: str,
        body: str,
        audience: EventAudience,
        source_revision: int,
        deduplication_key: str,
        now: datetime,
    ) -> PublishedContent:
        existing = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id, event_id, author_user_id, title, body,
                               audience_key, source_revision, published_at
                        FROM talaqi.event_updates
                        WHERE deduplication_key = :deduplication_key
                        """
                    ),
                    {"deduplication_key": deduplication_key},
                )
            )
            .mappings()
            .one_or_none()
        )
        if existing is not None:
            if (
                existing["event_id"] != event_id
                or existing["author_user_id"] != author_user_id
                or existing["title"] != title
                or existing["body"] != body
                or existing["audience_key"] != audience
                or existing["source_revision"] != source_revision
            ):
                raise ApiError(
                    code="idempotency_conflict",
                    message_key="errors.conflict",
                    status_code=409,
                )
            return _content(existing)
        current_revision = await self._session.scalar(
            text("SELECT revision FROM talaqi.events WHERE id = :event_id FOR UPDATE"),
            {"event_id": event_id},
        )
        if current_revision != source_revision:
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        INSERT INTO talaqi.event_updates (
                            id, event_id, author_user_id, title, body, audience_key,
                            deduplication_key, source_revision, published_at
                        ) VALUES (
                            :id, :event_id, :author_user_id, :title, :body, :audience,
                            :deduplication_key, :source_revision, :now
                        )
                        ON CONFLICT (deduplication_key) DO UPDATE
                        SET deduplication_key = talaqi.event_updates.deduplication_key
                        RETURNING id, event_id, author_user_id, title, body,
                                  audience_key, source_revision, published_at
                        """
                    ),
                    {
                        "id": generate_uuid7(),
                        "event_id": event_id,
                        "author_user_id": author_user_id,
                        "title": title,
                        "body": body,
                        "audience": audience,
                        "deduplication_key": deduplication_key,
                        "source_revision": source_revision,
                        "now": now,
                    },
                )
            )
            .mappings()
            .one()
        )
        if (
            row["event_id"] != event_id
            or row["author_user_id"] != author_user_id
            or row["title"] != title
            or row["body"] != body
            or row["audience_key"] != audience
            or row["source_revision"] != source_revision
        ):
            raise ApiError(
                code="idempotency_conflict", message_key="errors.conflict", status_code=409
            )
        item = _content(row)
        recipients = await self._event_recipients(event_id, audience)
        await self._snapshot_recipients("event_update", item.id, recipients)
        await self._publish_recipients(
            recipients,
            aggregate_type="event_update",
            aggregate_id=item.id,
            event_type="event.update_published",
            payload={"event_id": str(event_id), "event_update_id": str(item.id)},
            now=item.published_at,
        )
        return item

    async def list_club(self, club_id: UUID, user_id: UUID) -> tuple[PublishedContent, ...]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT announcement.id, announcement.title, announcement.body,
                               announcement.audience_key, announcement.published_at
                        FROM talaqi.announcements AS announcement
                        JOIN talaqi.announcement_recipients AS recipient
                          ON recipient.announcement_id = announcement.id
                         AND recipient.recipient_user_id = :user_id
                        WHERE announcement.club_id = :scope_id
                        ORDER BY announcement.published_at DESC, announcement.id DESC
                        LIMIT 100
                        """
                    ),
                    {"scope_id": club_id, "user_id": user_id},
                )
            )
            .mappings()
            .all()
        )
        return tuple(_content(row) for row in rows)

    async def list_event(
        self, event_id: UUID, user_id: UUID, *, manager: bool = False
    ) -> tuple[PublishedContent, ...]:
        audience_filter = (
            ""
            if manager
            else """
            AND EXISTS (
                SELECT 1 FROM talaqi.event_update_recipients AS recipient
                WHERE recipient.event_update_id = event_update.id
                  AND recipient.recipient_user_id = :user_id
            )
        """
        )
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT event_update.id, event_update.title, event_update.body,
                               event_update.audience_key, event_update.published_at
                        FROM talaqi.event_updates AS event_update
                        WHERE event_update.event_id = :scope_id
                        """
                        + audience_filter
                        + " ORDER BY event_update.published_at DESC, event_update.id DESC LIMIT 100"
                    ),
                    {"scope_id": event_id, "user_id": user_id},
                )
            )
            .mappings()
            .all()
        )
        return tuple(_content(row) for row in rows)

    async def is_club_member(self, club_id: UUID, user_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM talaqi.club_memberships "
                    "WHERE club_id = :scope_id AND user_id = :user_id)"
                ),
                {"scope_id": club_id, "user_id": user_id},
            )
        )

    async def can_view_event_updates(self, event_id: UUID, user_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM talaqi.registrations
                        WHERE event_id = :scope_id AND user_id = :user_id
                          AND state IN ('confirmed', 'cash_pending', 'waitlisted')
                    ) OR EXISTS (
                        SELECT 1
                        FROM talaqi.event_update_recipients AS recipient
                        JOIN talaqi.event_updates AS event_update
                          ON event_update.id = recipient.event_update_id
                        WHERE event_update.event_id = :scope_id
                          AND recipient.recipient_user_id = :user_id
                    )
                    """
                ),
                {"scope_id": event_id, "user_id": user_id},
            )
        )

    async def _club_recipients(self, club_id: UUID, audience: ClubAudience) -> list[UUID]:
        role_filter = "AND role IN ('owner', 'admin')" if audience == "admins" else ""
        return list(
            (
                await self._session.execute(
                    text(
                        "SELECT user_id FROM talaqi.club_memberships "
                        "WHERE club_id = :scope_id " + role_filter
                    ),
                    {"scope_id": club_id},
                )
            ).scalars()
        )

    async def _event_recipients(self, event_id: UUID, audience: EventAudience) -> list[UUID]:
        condition = (
            "state IN ('confirmed', 'cash_pending', 'waitlisted')"
            if audience == "all_active"
            else "state = CAST(:audience AS talaqi.registration_state)"
        )
        return list(
            (
                await self._session.execute(
                    text(
                        "SELECT user_id FROM talaqi.registrations "
                        f"WHERE event_id = :scope_id AND {condition}"
                    ),
                    {"scope_id": event_id, "audience": audience},
                )
            ).scalars()
        )

    async def _publish_recipients(
        self,
        recipients: list[UUID],
        *,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        payload: dict[str, object],
        now: datetime,
    ) -> None:
        publisher = TransactionalEventPublisher(self._session)
        for recipient in recipients:
            await publisher.publish(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload={**payload, "recipient_user_id": str(recipient)},
                deduplication_key=f"{event_type}:{aggregate_id}:{recipient}",
                available_at=now,
            )

    async def _snapshot_recipients(
        self,
        kind: Literal["announcement", "event_update"],
        content_id: UUID,
        recipients: list[UUID],
    ) -> None:
        if not recipients:
            return
        table = f"{kind}_recipients"
        parent_column = f"{kind}_id"
        await self._session.execute(
            text(
                f"INSERT INTO talaqi.{table} ({parent_column}, recipient_user_id) "
                f"SELECT :content_id, recipient FROM "
                "unnest(CAST(:recipients AS uuid[])) AS recipient "
                "ON CONFLICT DO NOTHING"
            ),
            {"content_id": content_id, "recipients": recipients},
        )


def _content(row: object) -> PublishedContent:
    value = cast(dict[str, object], row)
    return PublishedContent(
        id=cast(UUID, value["id"]),
        title=cast(str, value["title"]),
        body=cast(str, value["body"]),
        audience_key=cast(str, value["audience_key"]),
        published_at=cast(datetime, value["published_at"]),
    )


__all__ = [
    "ClubAudience",
    "EventAudience",
    "OrganizerContentRepository",
    "PublishedContent",
]
