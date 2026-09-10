from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from talaqi.audit import AuditService
from talaqi.db.identifiers import generate_uuid7, validate_uuid7
from talaqi.events.models import (
    Event,
    EventPatch,
    EventReferences,
    EventStatus,
    EventValidationError,
    NewEvent,
    apply_event_patch,
    normalize_new_event,
    validate_publishable,
    validate_published_event,
)
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.profiles.schemas import Capabilities
from talaqi.regions.models import RegionPolicy
from talaqi.settings.service import PlatformSettingsService

_CREATE_BLOCKERS = (
    "account_unavailable",
    "email_verification_required",
    "profile_incomplete",
    "rules_acceptance_required",
    "region_unavailable",
    "independent_event_limit_reached",
)


class EventRepositoryProtocol(Protocol):
    async def lock_creation(self, user_id: UUID) -> None: ...

    async def resolve_references(
        self,
        *,
        category_slug: str | None,
        country_code: str | None,
        city_slug: str | None,
    ) -> EventReferences: ...

    async def create(self, event: Event, *, references: EventReferences) -> Event: ...

    async def get(self, event_id: UUID, *, for_update: bool = False) -> Event | None: ...

    async def list_managed(self, user_id: UUID) -> list[Event]: ...

    async def update(
        self,
        event: Event,
        *,
        references: EventReferences,
        expected_revision: int,
    ) -> Event: ...

    async def transition(
        self,
        event_id: UUID,
        *,
        expected_revision: int,
        status: str,
        occurred_at: datetime,
    ) -> Event: ...

    async def delete_draft(self, event_id: UUID, *, expected_revision: int) -> bool: ...

    async def revoke_invite_tokens(self, event_id: UUID, *, occurred_at: datetime) -> None: ...


class EventEligibility(Protocol):
    async def evaluate(self, principal: AuthPrincipal) -> Capabilities: ...


class EventRegions(Protocol):
    async def get(self, country_code: str) -> RegionPolicy: ...


class ClubEventAccess(Protocol):
    async def require_event_manager(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        *,
        for_update: bool = False,
    ) -> None: ...


class EventMedia(Protocol):
    async def require_verified_owned(self, asset_id: UUID, owner_user_id: UUID) -> object: ...


def _not_found() -> ApiError:
    return ApiError(code="not_found", message_key="errors.not_found", status_code=404)


def _forbidden(code: str = "forbidden") -> ApiError:
    return ApiError(code=code, message_key=f"blockers.{code}", status_code=403)


def _invalid(code: str = "invalid_event") -> ApiError:
    return ApiError(code=code, message_key="errors.validation", status_code=422)


def _transition_error() -> ApiError:
    return ApiError(
        code="invalid_event_transition",
        message_key="errors.conflict",
        status_code=409,
    )


class EventService:
    def __init__(
        self,
        repository: EventRepositoryProtocol,
        eligibility: EventEligibility,
        regions: EventRegions,
        clubs: ClubEventAccess,
        media: EventMedia,
        audit: AuditService,
        feature_flags: PlatformSettingsService | None = None,
    ) -> None:
        self._repository = repository
        self._eligibility = eligibility
        self._regions = regions
        self._clubs = clubs
        self._media = media
        self._audit = audit
        self._feature_flags = feature_flags

    async def list_managed(self, principal: AuthPrincipal) -> list[Event]:
        return await self._repository.list_managed(principal.user_id)

    async def create(
        self,
        principal: AuthPrincipal,
        value: NewEvent,
        *,
        request_id: UUID,
        now: datetime | None = None,
    ) -> Event:
        current = now or datetime.now(UTC)
        try:
            normalized = normalize_new_event(value)
        except EventValidationError as error:
            raise _invalid(error.code) from None
        await self._repository.lock_creation(principal.user_id)
        capabilities = await self._eligibility.evaluate(principal)
        await self._authorize_creation(principal, normalized, capabilities)
        policy = await self._policy(normalized.country_code)
        event = self._new_record(principal, normalized, current)
        if normalized.publish:
            if policy is None:
                raise _invalid("event_not_publishable")
            event = self._with_policy_defaults(event, policy)
            self._validate_publishable(event, policy, current)
        elif policy is not None:
            self._validate_draft_policy(event, policy)
        if event.cover_media_id is not None:
            await self._media.require_verified_owned(event.cover_media_id, principal.user_id)
        references = await self._repository.resolve_references(
            category_slug=event.category_slug,
            country_code=event.country_code,
            city_slug=event.city_slug,
        )
        created = await self._repository.create(event, references=references)
        await self._record(
            principal,
            "event.create",
            created,
            request_id,
            safe_before=None,
        )
        if created.status == "published":
            await self._record(
                principal,
                "event.publish",
                created,
                request_id,
                safe_before={"status": "draft", "revision": 0},
            )
        return created

    async def get(self, principal: AuthPrincipal, event_id: UUID) -> Event:
        event = await self._find(event_id)
        await self._authorize_manager(principal, event)
        return event

    async def authorize_replay(self, principal: AuthPrincipal, event_id: UUID) -> None:
        event = await self._find(event_id, for_update=True)
        await self._authorize_manager(principal, event, for_update=True)

    async def update(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        patch: EventPatch,
        *,
        request_id: UUID,
        now: datetime | None = None,
    ) -> Event:
        event = await self._find(event_id, for_update=True)
        await self._authorize_manager(principal, event, for_update=True)
        if event.status not in ("draft", "published"):
            raise _transition_error()
        if patch.revision != event.revision:
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        try:
            candidate = apply_event_patch(event, patch)
        except EventValidationError as error:
            raise _invalid(error.code) from None
        publishing = event.status == "draft" and patch.publish is True
        if event.status == "published" and "publish" in patch.changed_fields:
            raise _transition_error()
        current = now or datetime.now(UTC)
        policy = await self._policy(candidate.country_code)
        if publishing:
            if policy is None:
                raise _invalid("event_not_publishable")
            candidate = replace(candidate, status="published", published_at=current)
            candidate = self._with_policy_defaults(candidate, policy)
            self._validate_publishable(candidate, policy, current)
        elif event.status == "published":
            if policy is None:
                raise _invalid("event_not_publishable")
            if "start_at" in patch.changed_fields:
                self._validate_publishable(candidate, policy, current)
            else:
                self._validate_published_event(candidate, policy)
        elif policy is not None:
            self._validate_draft_policy(candidate, policy)
        if "cover_media_id" in patch.changed_fields and candidate.cover_media_id is not None:
            await self._media.require_verified_owned(candidate.cover_media_id, principal.user_id)
        references = await self._repository.resolve_references(
            category_slug=candidate.category_slug,
            country_code=candidate.country_code,
            city_slug=candidate.city_slug,
        )
        updated = await self._repository.update(
            candidate,
            references=references,
            expected_revision=patch.revision,
        )
        if event.visibility == "private_link" and updated.visibility != "private_link":
            await self._repository.revoke_invite_tokens(updated.id, occurred_at=current)
        await self._record(
            principal,
            "event.update",
            updated,
            request_id,
            safe_before={"status": event.status, "revision": event.revision},
        )
        if publishing:
            await self._record(
                principal,
                "event.publish",
                updated,
                request_id,
                safe_before={"status": "draft", "revision": event.revision},
            )
        return updated

    async def cancel(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        *,
        revision: int,
        request_id: UUID,
        now: datetime | None = None,
    ) -> Event:
        return await self._transition(
            principal,
            event_id,
            revision=revision,
            target="cancelled",
            request_id=request_id,
            now=now,
        )

    async def complete(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        *,
        revision: int,
        request_id: UUID,
        now: datetime | None = None,
    ) -> Event:
        return await self._transition(
            principal,
            event_id,
            revision=revision,
            target="completed",
            request_id=request_id,
            now=now,
        )

    async def delete_draft(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        *,
        revision: int,
        request_id: UUID,
    ) -> None:
        event = await self._find(event_id, for_update=True)
        await self._authorize_manager(principal, event, for_update=True)
        if event.status != "draft":
            raise _transition_error()
        if revision != event.revision:
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        if not await self._repository.delete_draft(event.id, expected_revision=revision):
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="event.delete_draft",
            target_type="event",
            target_id=event.id,
            safe_before={"status": event.status, "revision": event.revision},
            request_id=request_id,
        )

    async def duplicate(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        *,
        request_id: UUID,
        now: datetime | None = None,
    ) -> Event:
        source = await self._find(event_id, for_update=True)
        await self._authorize_manager(principal, source, for_update=True)
        await self._repository.lock_creation(principal.user_id)
        capabilities = await self._eligibility.evaluate(principal)
        value = NewEvent(
            ownership_type=source.ownership_type,
            club_id=source.club_id,
            title=source.title,
            description=source.description,
            category_slug=source.category_slug,
            country_code=source.country_code,
            city_slug=source.city_slug,
            start_at=source.start_at,
            end_at=source.end_at,
            time_zone=source.time_zone,
            capacity=source.capacity,
            visibility=source.visibility,
            registration_method=source.registration_method,
            cash_expiry_minutes=source.cash_expiry_minutes,
            cancellation_cutoff_minutes=source.cancellation_cutoff_minutes,
            district=source.district,
            public_meeting_area=source.public_meeting_area,
            exact_address=source.exact_address,
            latitude=source.latitude,
            longitude=source.longitude,
            exact_venue_is_public=source.exact_venue_is_public,
            cover_media_id=source.cover_media_id,
            publish=False,
        )
        await self._authorize_creation(principal, value, capabilities)
        current = now or datetime.now(UTC)
        duplicate = replace(
            source,
            id=generate_uuid7(),
            owner_user_id=(principal.user_id if source.ownership_type == "independent" else None),
            status="draft",
            revision=1,
            published_at=None,
            cancelled_at=None,
            completed_at=None,
            suspended_at=None,
            suspension_reason=None,
            created_at=current,
            updated_at=current,
        )
        references = await self._repository.resolve_references(
            category_slug=duplicate.category_slug,
            country_code=duplicate.country_code,
            city_slug=duplicate.city_slug,
        )
        created = await self._repository.create(duplicate, references=references)
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="event.duplicate",
            target_type="event",
            target_id=created.id,
            safe_before={"source_event_id": str(source.id)},
            safe_after={"status": "draft", "revision": 1},
            request_id=request_id,
        )
        return created

    async def _transition(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        *,
        revision: int,
        target: EventStatus,
        request_id: UUID,
        now: datetime | None,
    ) -> Event:
        event = await self._find(event_id, for_update=True)
        await self._authorize_manager(principal, event, for_update=True)
        if revision != event.revision:
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        current = now or datetime.now(UTC)
        if event.status != "published":
            raise _transition_error()
        if target == "completed" and (event.end_at is None or current < event.end_at):
            raise _transition_error()
        updated = await self._repository.transition(
            event.id,
            expected_revision=revision,
            status=target,
            occurred_at=current,
        )
        await self._record(
            principal,
            f"event.{target}",
            updated,
            request_id,
            safe_before={"status": event.status, "revision": event.revision},
        )
        return updated

    async def _authorize_creation(
        self,
        principal: AuthPrincipal,
        event: NewEvent,
        capabilities: Capabilities,
    ) -> None:
        if principal.status != "active":
            raise _forbidden()
        if event.ownership_type == "independent":
            if self._feature_flags is not None:
                await self._feature_flags.require_enabled(
                    "features.independent_event_creation_enabled"
                )
            if not capabilities.create_independent_event:
                blocker = next(
                    (item for item in _CREATE_BLOCKERS if item in capabilities.blockers),
                    "forbidden",
                )
                raise _forbidden(blocker)
            return
        if not capabilities.save_event:
            blocker = next(
                (item for item in _CREATE_BLOCKERS if item in capabilities.blockers),
                "forbidden",
            )
            raise _forbidden(blocker)
        if event.club_id is None:
            raise _invalid()
        await self._clubs.require_event_manager(
            principal,
            event.club_id,
            for_update=True,
        )

    async def _authorize_manager(
        self,
        principal: AuthPrincipal,
        event: Event,
        *,
        for_update: bool = False,
    ) -> None:
        if principal.status != "active" or event.status == "suspended":
            raise _forbidden()
        if event.ownership_type == "independent":
            if event.club_id is not None or event.owner_user_id != principal.user_id:
                raise _forbidden()
            return
        if event.owner_user_id is not None or event.club_id is None:
            raise _forbidden()
        await self._clubs.require_event_manager(
            principal,
            event.club_id,
            for_update=for_update,
        )

    async def _find(self, event_id: UUID, *, for_update: bool = False) -> Event:
        try:
            identifier = validate_uuid7(event_id)
        except ValueError:
            raise _not_found() from None
        event = await self._repository.get(identifier, for_update=for_update)
        if event is None:
            raise _not_found()
        return event

    async def _policy(self, country_code: str | None) -> RegionPolicy | None:
        if country_code is None:
            return None
        return await self._regions.get(country_code)

    @staticmethod
    def _with_policy_defaults(event: Event, policy: RegionPolicy) -> Event:
        return replace(
            event,
            cash_expiry_minutes=(
                policy.cash_default_minutes
                if event.registration_method == "cash_organizer_confirmed"
                and event.cash_expiry_minutes is None
                else event.cash_expiry_minutes
            ),
            cancellation_cutoff_minutes=(
                policy.cancellation_default_minutes
                if event.cancellation_cutoff_minutes is None
                else event.cancellation_cutoff_minutes
            ),
        )

    @staticmethod
    def _validate_draft_policy(event: Event, policy: RegionPolicy) -> None:
        if (
            event.registration_method is not None
            and event.registration_method not in policy.allowed_registration_methods
        ):
            raise _invalid("registration_method_not_allowed")
        if event.registration_method == "cash_organizer_confirmed" and (
            event.cash_expiry_minutes is not None
            and not policy.cash_bounds[0] <= event.cash_expiry_minutes <= policy.cash_bounds[1]
        ):
            raise _invalid("invalid_event_deadline")
        if event.cancellation_cutoff_minutes is not None and not (
            policy.cancellation_bounds[0]
            <= event.cancellation_cutoff_minutes
            <= policy.cancellation_bounds[1]
        ):
            raise _invalid("invalid_event_deadline")

    @staticmethod
    def _validate_publishable(event: Event, policy: RegionPolicy, now: datetime) -> None:
        try:
            validate_publishable(event, policy, now=now)
        except EventValidationError as error:
            raise _invalid(error.code) from None

    @staticmethod
    def _validate_published_event(event: Event, policy: RegionPolicy) -> None:
        try:
            validate_published_event(event, policy)
        except EventValidationError as error:
            raise _invalid(error.code) from None

    @staticmethod
    def _new_record(principal: AuthPrincipal, value: NewEvent, now: datetime) -> Event:
        status: EventStatus = "published" if value.publish else "draft"
        return Event(
            id=generate_uuid7(),
            ownership_type=value.ownership_type,
            club_id=value.club_id,
            owner_user_id=(principal.user_id if value.ownership_type == "independent" else None),
            title=value.title,
            description=value.description,
            category_slug=value.category_slug,
            country_code=value.country_code,
            city_slug=value.city_slug,
            start_at=value.start_at,
            end_at=value.end_at,
            time_zone=value.time_zone,
            capacity=value.capacity,
            visibility=value.visibility,
            status=status,
            registration_method=value.registration_method,
            cash_expiry_minutes=value.cash_expiry_minutes,
            cancellation_cutoff_minutes=value.cancellation_cutoff_minutes,
            district=value.district,
            public_meeting_area=value.public_meeting_area,
            exact_address=value.exact_address,
            latitude=value.latitude,
            longitude=value.longitude,
            exact_venue_is_public=value.exact_venue_is_public,
            cover_media_id=value.cover_media_id,
            revision=1,
            published_at=now if status == "published" else None,
            cancelled_at=None,
            completed_at=None,
            suspended_at=None,
            suspension_reason=None,
            created_at=now,
            updated_at=now,
        )

    async def _record(
        self,
        principal: AuthPrincipal,
        action: str,
        event: Event,
        request_id: UUID,
        *,
        safe_before: dict[str, object] | None,
    ) -> None:
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action=action,
            target_type="event",
            target_id=event.id,
            safe_before=safe_before,
            safe_after={"status": event.status, "revision": event.revision},
            request_id=request_id,
        )


__all__ = ["EventRepositoryProtocol", "EventService"]
