from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from talaqi.audit import AuditService
from talaqi.db.identifiers import generate_uuid7
from talaqi.events.access_models import (
    EventAudienceProjection,
    EventCancellationTerms,
    EventRegistrationTerms,
    ManagerVenueProjection,
)
from talaqi.events.access_repository import EventAccessRepository
from talaqi.events.access_tokens import PrivateLinkTokenCodec
from talaqi.events.models import Event
from talaqi.events.repository import EventRepository
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError

_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")


class ClubManagerAccess(Protocol):
    async def require_event_manager(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        *,
        for_update: bool = False,
    ) -> None: ...

    async def require_registration_available(self, club_id: UUID, *, for_update: bool) -> None: ...


def _not_found() -> ApiError:
    return ApiError(code="not_found", message_key="errors.not_found", status_code=404)


def _forbidden() -> ApiError:
    return ApiError(code="forbidden", message_key="errors.forbidden", status_code=403)


class EventAccessService:
    def __init__(
        self,
        repository: EventAccessRepository,
        events: EventRepository,
        clubs: ClubManagerAccess,
        audit: AuditService,
        codec: PrivateLinkTokenCodec,
    ) -> None:
        self._repository = repository
        self._events = events
        self._clubs = clubs
        self._audit = audit
        self._codec = codec

    async def issue(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        *,
        expires_in_days: int,
        rotate: bool,
        request_id: UUID,
        now: datetime | None = None,
    ) -> tuple[str, datetime]:
        current = now or datetime.now(UTC)
        event = await self._events.get(event_id, for_update=True)
        if event is None:
            raise _not_found()
        await self._authorize_manager(principal, event, for_update=True)
        if (
            event.status != "published"
            or event.visibility != "private_link"
            or event.suspended_at is not None
        ):
            raise ApiError(
                code="private_link_unavailable",
                message_key="errors.conflict",
                status_code=409,
            )
        raw_token = self._codec.issue()
        expires_at = current + timedelta(days=expires_in_days)
        created = await self._repository.create_link(
            link_id=generate_uuid7(),
            event_id=event.id,
            actor_id=principal.user_id,
            token_hash=self._codec.digest(raw_token),
            expires_at=expires_at,
            now=current,
            rotate=rotate,
        )
        if created is None:
            raise ApiError(
                code="private_link_exists",
                message_key="errors.conflict",
                status_code=409,
            )
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="event.private_link.rotate" if rotate else "event.private_link.create",
            target_type="event",
            target_id=event.id,
            safe_after={
                "expires_at": expires_at.isoformat(),
                "status": event.status,
                "visibility": event.visibility,
            },
            request_id=request_id,
        )
        return raw_token, expires_at

    async def revoke(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        *,
        request_id: UUID,
        now: datetime | None = None,
    ) -> None:
        current = now or datetime.now(UTC)
        event = await self._events.get(event_id, for_update=True)
        if event is None:
            raise _not_found()
        await self._authorize_manager(principal, event, for_update=True)
        changed = await self._repository.revoke_links(event.id, now=current)
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="event.private_link.revoke",
            target_type="event",
            target_id=event.id,
            safe_after={"active_link_revoked": changed},
            request_id=request_id,
        )

    async def resolve(
        self,
        raw_token: str,
        *,
        principal: AuthPrincipal | None,
        now: datetime | None = None,
    ) -> EventAudienceProjection:
        current = now or datetime.now(UTC)
        if _TOKEN.fullmatch(raw_token) is None:
            raise _not_found()
        event_id = await self._repository.resolve_link(self._codec.digest(raw_token), now=current)
        if event_id is None:
            raise _not_found()
        projection = await self._repository.project(
            event_id,
            caller_id=principal.user_id if principal else None,
            visibility="private_link",
            now=current,
        )
        if projection is None:
            raise _not_found()
        return projection

    async def public(
        self,
        event_id: UUID,
        *,
        principal: AuthPrincipal | None,
        now: datetime | None = None,
    ) -> EventAudienceProjection:
        projection = await self._repository.project(
            event_id,
            caller_id=principal.user_id if principal else None,
            visibility="public",
            now=now or datetime.now(UTC),
        )
        if projection is None:
            raise _not_found()
        return projection

    async def managed(
        self,
        principal: AuthPrincipal,
        event: Event,
        *,
        now: datetime | None = None,
    ) -> ManagerVenueProjection:
        await self._authorize_manager(principal, event, for_update=False)
        projection = await self._repository.project_manager_venue(event.id)
        if projection is None:
            raise _not_found()
        return projection

    async def registration_terms(
        self,
        event_id: UUID,
        *,
        private_link_hash: bytes | None,
        now: datetime,
    ) -> EventRegistrationTerms:
        event = await self._events.get(event_id, for_update=True)
        if event is None or event.status != "published" or event.suspended_at is not None:
            raise _not_found()
        if event.ownership_type == "club":
            if event.club_id is None:
                raise _not_found()
            await self._clubs.require_registration_available(event.club_id, for_update=True)
        if event.visibility == "private_link" and (
            private_link_hash is None
            or not await self._repository.authorize_registration_link(
                event.id, private_link_hash, now=now
            )
        ):
            raise _not_found()
        if event.start_at is None or event.registration_method is None:
            raise _not_found()
        return EventRegistrationTerms(
            id=event.id,
            start_at=event.start_at,
            capacity=event.capacity,
            method=event.registration_method,
            cash_expiry_minutes=event.cash_expiry_minutes,
        )

    async def cancellation_terms(
        self,
        event_id: UUID,
    ) -> EventCancellationTerms:
        event = await self._events.get(event_id, for_update=True)
        if (
            event is None
            or event.status != "published"
            or event.start_at is None
            or event.registration_method is None
            or event.cancellation_cutoff_minutes is None
        ):
            raise _not_found()
        return EventCancellationTerms(
            id=event.id,
            start_at=event.start_at,
            capacity=event.capacity,
            method=event.registration_method,
            cash_expiry_minutes=event.cash_expiry_minutes,
            cancellation_cutoff_minutes=event.cancellation_cutoff_minutes,
        )

    async def _authorize_manager(
        self,
        principal: AuthPrincipal,
        event: Event,
        *,
        for_update: bool,
    ) -> None:
        if principal.status != "active" or event.status == "suspended":
            raise _forbidden()
        if event.ownership_type == "independent":
            if event.club_id is not None or event.owner_user_id != principal.user_id:
                raise _forbidden()
            return
        if (
            event.ownership_type != "club"
            or event.club_id is None
            or event.owner_user_id is not None
        ):
            raise _forbidden()
        await self._clubs.require_event_manager(
            principal,
            event.club_id,
            for_update=for_update,
        )


__all__ = ["EventAccessService"]
