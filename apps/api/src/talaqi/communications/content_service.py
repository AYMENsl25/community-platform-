from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from talaqi.clubs.event_access import ClubEventAccessService
from talaqi.communications.content import OrganizerContentRepository, PublishedContent
from talaqi.communications.content_schemas import ClubAnnouncementRequest, EventUpdateRequest
from talaqi.events.access_service import EventAccessService
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.settings.service import PlatformSettingsService


class OrganizerCommunicationsService:
    def __init__(
        self,
        repository: OrganizerContentRepository,
        club_access: ClubEventAccessService,
        event_access: EventAccessService,
        feature_flags: PlatformSettingsService | None = None,
    ) -> None:
        self._repository = repository
        self._club_access = club_access
        self._event_access = event_access
        self._feature_flags = feature_flags

    async def create_club(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        body: ClubAnnouncementRequest,
        idempotency_key: str,
    ) -> PublishedContent:
        await self._club_access.require_event_manager(principal, club_id, for_update=True)
        if self._feature_flags is None:
            raise RuntimeError("announcement creation requires feature flag service")
        await self._feature_flags.require_enabled("features.organizer_announcements_enabled")
        return await self._repository.create_club_announcement(
            club_id=club_id,
            author_user_id=principal.user_id,
            title=body.title,
            body=body.body,
            audience=body.audience,
            deduplication_key=f"club-announcement:{principal.user_id}:{idempotency_key}",
            now=datetime.now(UTC),
        )

    async def list_club(
        self, principal: AuthPrincipal, club_id: UUID
    ) -> tuple[PublishedContent, ...]:
        if not await self._repository.is_club_member(club_id, principal.user_id):
            raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
        return await self._repository.list_club(club_id, principal.user_id)

    async def create_event(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        body: EventUpdateRequest,
        idempotency_key: str,
    ) -> PublishedContent:
        await self._event_access.require_manager(principal, event_id, for_update=True)
        return await self._repository.create_event_update(
            event_id=event_id,
            author_user_id=principal.user_id,
            title=body.title,
            body=body.body,
            audience=body.audience,
            source_revision=body.revision,
            deduplication_key=f"event-update:{principal.user_id}:{idempotency_key}",
            now=datetime.now(UTC),
        )

    async def list_event(
        self, principal: AuthPrincipal, event_id: UUID
    ) -> tuple[PublishedContent, ...]:
        manager = False
        try:
            await self._event_access.require_manager(principal, event_id, for_update=False)
            manager = True
        except ApiError:
            if not await self._repository.can_view_event_updates(event_id, principal.user_id):
                raise ApiError(
                    code="not_found", message_key="errors.not_found", status_code=404
                ) from None
        return await self._repository.list_event(event_id, principal.user_id, manager=manager)


__all__ = ["OrganizerCommunicationsService"]
