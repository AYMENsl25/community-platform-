from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from talaqi.communications.repository import NotificationRepository
from talaqi.outbox import OutboxEvent

SECURITY_EVENTS = frozenset(
    {"identity.email_verification_requested", "identity.password_reset_requested"}
)
REGISTRATION_EVENTS = frozenset(
    {
        "registration.confirmed",
        "registration.cash_pending",
        "registration.waitlisted",
        "registration.cancelled",
        "registration.expired",
    }
)
COMMUNITY_EVENTS = frozenset(
    {
        "membership.requested",
        "membership.approved",
        "membership.rejected",
        "membership.removed",
    }
)
EVENT_EVENTS = frozenset({"event.updated", "event.cancelled"})
CONTENT_EVENTS = frozenset({"club.announcement_published", "event.update_published"})
MODERATION_EVENTS = frozenset({"moderation.case_updated", "moderation.action_taken"})
SUPPORTED_NOTIFICATION_EVENTS = (
    SECURITY_EVENTS
    | REGISTRATION_EVENTS
    | COMMUNITY_EVENTS
    | EVENT_EVENTS
    | CONTENT_EVENTS
    | MODERATION_EVENTS
)
_SAFE_PARAMETER_KEYS = frozenset(
    {
        "event_id",
        "registration_id",
        "state",
        "previous_state",
        "reason_code",
        "club_id",
        "membership_id",
        "case_id",
        "announcement_id",
        "event_update_id",
    }
)


class NotificationProjectionHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def deliver(self, event: OutboxEvent) -> None:
        recipient = _recipient(event)
        category = _category(event.event_type)
        parameters = {
            key: value for key, value in event.payload.items() if key in _SAFE_PARAMETER_KEYS
        }
        source_type, source_id = _source(event, parameters)
        action_path = _action_path(parameters)
        async with self._session_factory() as session, session.begin():
            await NotificationRepository(session).project(
                event,
                recipient_user_id=recipient,
                category=category,
                title_key=f"notifications.{category}.title",
                body_key=f"notifications.{event.event_type}.body",
                parameters=parameters,
                action_path=action_path,
                source_type=source_type,
                source_id=source_id,
            )


def _recipient(event: OutboxEvent) -> UUID:
    raw = event.payload.get("recipient_user_id", event.payload.get("user_id"))
    if not isinstance(raw, str):
        raise ValueError("notification_recipient_missing")
    return UUID(raw)


def _category(event_type: str) -> str:
    if event_type in SECURITY_EVENTS or event_type in MODERATION_EVENTS:
        return "security"
    if event_type in REGISTRATION_EVENTS or event_type in EVENT_EVENTS:
        return "event"
    if event_type in COMMUNITY_EVENTS or event_type == "club.announcement_published":
        return "community"
    if event_type == "event.update_published":
        return "event"
    raise ValueError("unsupported_notification_event")


def _source(event: OutboxEvent, parameters: dict[str, object]) -> tuple[str | None, UUID | None]:
    for key, source_type in (
        ("registration_id", "registration"),
        ("event_id", "event"),
        ("club_id", "club"),
        ("case_id", "moderation_case"),
    ):
        value = parameters.get(key)
        if isinstance(value, str):
            return source_type, UUID(value)
    return event.aggregate_type, event.aggregate_id


def _action_path(parameters: dict[str, object]) -> str | None:
    event_id = parameters.get("event_id")
    if isinstance(event_id, str):
        return f"/events/{event_id}"
    club_id = parameters.get("club_id")
    if isinstance(club_id, str):
        return f"/clubs/{club_id}"
    return None


__all__ = ["SUPPORTED_NOTIFICATION_EVENTS", "NotificationProjectionHandler"]
