from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.events.models import (
    Event,
    EventOwnershipType,
    EventReferences,
    EventStatus,
    EventVisibility,
    RegistrationMethod,
)
from talaqi.platform import ApiError

_EVENT_SELECT = """
SELECT event.id, event.ownership_type::text AS ownership_type,
       event.club_id, event.owner_user_id, event.title, event.description,
       category.slug AS category_slug, country.code AS country_code,
       city.slug AS city_slug, event.start_at, event.end_at, event.time_zone,
       event.capacity, event.visibility::text AS visibility,
       event.status::text AS status,
       event.registration_method::text AS registration_method,
       event.cash_expiry_minutes, event.cancellation_cutoff_minutes,
       event.district, event.public_meeting_area, event.exact_address,
       event.latitude, event.longitude, event.exact_venue_is_public,
       event.cover_media_id, event.revision, event.published_at,
       event.cancelled_at, event.completed_at, event.suspended_at,
       event.suspension_reason, event.created_at, event.updated_at
FROM talaqi.events AS event
LEFT JOIN talaqi.categories AS category ON category.id = event.category_id
LEFT JOIN talaqi.countries AS country ON country.id = event.country_id
LEFT JOIN talaqi.cities AS city ON city.id = event.city_id
"""


def _invalid() -> ApiError:
    return ApiError(code="invalid_event", message_key="errors.validation", status_code=422)


def _stale() -> ApiError:
    return ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)


def _event(row: object) -> Event:
    values = cast(dict[str, object], row)
    latitude = values["latitude"]
    longitude = values["longitude"]
    return Event(
        id=cast(UUID, values["id"]),
        ownership_type=cast(EventOwnershipType, values["ownership_type"]),
        club_id=cast(UUID | None, values["club_id"]),
        owner_user_id=cast(UUID | None, values["owner_user_id"]),
        title=cast(str, values["title"]),
        description=cast(str, values["description"]),
        category_slug=cast(str | None, values["category_slug"]),
        country_code=(
            cast(str, values["country_code"]).strip()
            if values["country_code"] is not None
            else None
        ),
        city_slug=cast(str | None, values["city_slug"]),
        start_at=cast(object, values["start_at"]),  # type: ignore[arg-type]
        end_at=cast(object, values["end_at"]),  # type: ignore[arg-type]
        time_zone=cast(str | None, values["time_zone"]),
        capacity=cast(int | None, values["capacity"]),
        visibility=cast(EventVisibility, values["visibility"]),
        status=cast(EventStatus, values["status"]),
        registration_method=cast(RegistrationMethod | None, values["registration_method"]),
        cash_expiry_minutes=cast(int | None, values["cash_expiry_minutes"]),
        cancellation_cutoff_minutes=cast(int | None, values["cancellation_cutoff_minutes"]),
        district=cast(str | None, values["district"]),
        public_meeting_area=cast(str | None, values["public_meeting_area"]),
        exact_address=cast(str | None, values["exact_address"]),
        latitude=float(cast(Decimal, latitude)) if latitude is not None else None,
        longitude=float(cast(Decimal, longitude)) if longitude is not None else None,
        exact_venue_is_public=cast(bool, values["exact_venue_is_public"]),
        cover_media_id=cast(UUID | None, values["cover_media_id"]),
        revision=cast(int, values["revision"]),
        published_at=cast(object, values["published_at"]),  # type: ignore[arg-type]
        cancelled_at=cast(object, values["cancelled_at"]),  # type: ignore[arg-type]
        completed_at=cast(object, values["completed_at"]),  # type: ignore[arg-type]
        suspended_at=cast(object, values["suspended_at"]),  # type: ignore[arg-type]
        suspension_reason=cast(str | None, values["suspension_reason"]),
        created_at=cast(object, values["created_at"]),  # type: ignore[arg-type]
        updated_at=cast(object, values["updated_at"]),  # type: ignore[arg-type]
    )


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_creation(self, user_id: UUID) -> None:
        found = (
            await self._session.execute(
                text("SELECT id FROM talaqi.users WHERE id = :user_id FOR UPDATE"),
                {"user_id": user_id},
            )
        ).scalar_one_or_none()
        if found is None:
            raise ApiError(
                code="authentication_required",
                message_key="errors.authentication_required",
                status_code=401,
            )
        await self._session.execute(
            text(
                """
                SELECT policy.id
                FROM talaqi.profiles AS profile
                JOIN talaqi.countries AS country ON country.id = profile.country_id
                JOIN talaqi.regional_policies AS policy ON policy.country_id = country.id
                WHERE profile.user_id = :user_id
                FOR SHARE OF country, policy
                """
            ),
            {"user_id": user_id},
        )

    async def resolve_references(
        self,
        *,
        category_slug: str | None,
        country_code: str | None,
        city_slug: str | None,
    ) -> EventReferences:
        if city_slug is not None and country_code is None:
            raise _invalid()
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT
                            (SELECT id FROM talaqi.categories
                             WHERE slug = CAST(:category_slug AS text) AND enabled = true
                             FOR SHARE) AS category_id,
                            (SELECT id FROM talaqi.countries
                             WHERE code = CAST(:country_code AS char(2)) AND enabled = true
                             FOR SHARE) AS country_id,
                            (SELECT city.id
                             FROM talaqi.cities AS city
                             JOIN talaqi.countries AS country ON country.id = city.country_id
                             WHERE country.code = CAST(:country_code AS char(2))
                               AND city.slug = CAST(:city_slug AS text)
                               AND country.enabled = true
                               AND city.enabled = true AND city.beta_enabled = true
                             FOR SHARE OF country, city) AS city_id
                        """
                    ),
                    {
                        "category_slug": category_slug,
                        "country_code": country_code,
                        "city_slug": city_slug,
                    },
                )
            )
            .mappings()
            .one()
        )
        if category_slug is not None and row["category_id"] is None:
            raise _invalid()
        if country_code is not None and row["country_id"] is None:
            raise _invalid()
        if city_slug is not None and row["city_id"] is None:
            raise _invalid()
        return EventReferences(
            category_id=row["category_id"],
            country_id=row["country_id"],
            city_id=row["city_id"],
        )

    async def create(self, event: Event, *, references: EventReferences) -> Event:
        try:
            await self._session.execute(
                text(
                    """
                    INSERT INTO talaqi.events (
                        id, ownership_type, club_id, owner_user_id, title, description,
                        category_id, country_id, city_id, start_at, end_at, time_zone,
                        capacity, visibility, status, registration_method,
                        cash_expiry_minutes, cancellation_cutoff_minutes, district,
                        public_meeting_area, exact_address, latitude, longitude,
                        exact_venue_is_public, cover_media_id, revision, published_at,
                        cancelled_at, completed_at, suspended_at, suspension_reason,
                        created_at, updated_at
                    ) VALUES (
                        :id, CAST(:ownership_type AS talaqi.event_ownership_type),
                        :club_id, :owner_user_id, :title, :description,
                        :category_id, :country_id, :city_id, :start_at, :end_at, :time_zone,
                        :capacity, CAST(:visibility AS talaqi.event_visibility),
                        CAST(:status AS talaqi.event_status),
                        CAST(:registration_method AS talaqi.registration_method),
                        :cash_expiry_minutes, :cancellation_cutoff_minutes, :district,
                        :public_meeting_area, :exact_address, :latitude, :longitude,
                        :exact_venue_is_public, :cover_media_id, :revision, :published_at,
                        :cancelled_at, :completed_at, :suspended_at, :suspension_reason,
                        :created_at, :updated_at
                    )
                    """
                ),
                self._parameters(event, references),
            )
        except IntegrityError as error:
            raise _invalid() from error
        created = await self.get(event.id)
        if created is None:
            raise RuntimeError("created event could not be reloaded")
        return created

    async def get(self, event_id: UUID, *, for_update: bool = False) -> Event | None:
        statement = text(
            _EVENT_SELECT
            + " WHERE event.id = :event_id"
            + (" FOR UPDATE OF event" if for_update else "")
        )
        row = (
            (await self._session.execute(statement, {"event_id": event_id}))
            .mappings()
            .one_or_none()
        )
        return _event(dict(row)) if row is not None else None

    async def update(
        self,
        event: Event,
        *,
        references: EventReferences,
        expected_revision: int,
    ) -> Event:
        parameters = self._parameters(event, references)
        parameters["expected_revision"] = expected_revision
        updated = (
            await self._session.execute(
                text(
                    """
                    UPDATE talaqi.events
                    SET title = :title, description = :description,
                        category_id = :category_id, country_id = :country_id,
                        city_id = :city_id, start_at = :start_at, end_at = :end_at,
                        time_zone = :time_zone, capacity = :capacity,
                        visibility = CAST(:visibility AS talaqi.event_visibility),
                        status = CAST(:status AS talaqi.event_status),
                        registration_method = CAST(
                            :registration_method AS talaqi.registration_method
                        ),
                        cash_expiry_minutes = :cash_expiry_minutes,
                        cancellation_cutoff_minutes = :cancellation_cutoff_minutes,
                        district = :district, public_meeting_area = :public_meeting_area,
                        exact_address = :exact_address, latitude = :latitude,
                        longitude = :longitude,
                        exact_venue_is_public = :exact_venue_is_public,
                        cover_media_id = :cover_media_id, published_at = :published_at,
                        revision = revision + 1
                    WHERE id = :id AND revision = :expected_revision
                      AND status IN ('draft', 'published')
                    RETURNING id
                    """
                ),
                parameters,
            )
        ).scalar_one_or_none()
        if updated is None:
            raise _stale()
        result = await self.get(event.id)
        if result is None:
            raise RuntimeError("updated event could not be reloaded")
        return result

    async def transition(
        self,
        event_id: UUID,
        *,
        expected_revision: int,
        status: str,
        occurred_at: object,
    ) -> Event:
        if status not in ("cancelled", "completed"):
            raise ValueError("unsupported event transition")
        updated = (
            await self._session.execute(
                text(
                    """
                    UPDATE talaqi.events
                    SET status = CAST(:status AS talaqi.event_status),
                        cancelled_at = CASE WHEN :status = 'cancelled'
                                            THEN CAST(:occurred_at AS timestamptz)
                                            ELSE cancelled_at END,
                        completed_at = CASE WHEN :status = 'completed'
                                            THEN CAST(:occurred_at AS timestamptz)
                                            ELSE completed_at END,
                        revision = revision + 1
                    WHERE id = :event_id AND revision = :expected_revision
                      AND status = 'published'
                    RETURNING id
                    """
                ),
                {
                    "event_id": event_id,
                    "expected_revision": expected_revision,
                    "status": status,
                    "occurred_at": occurred_at,
                },
            )
        ).scalar_one_or_none()
        if updated is None:
            raise _stale()
        result = await self.get(event_id)
        if result is None:
            raise RuntimeError("transitioned event could not be reloaded")
        return result

    async def revoke_invite_tokens(self, event_id: UUID, *, occurred_at: datetime) -> None:
        await self._session.execute(
            text(
                """
                UPDATE talaqi.event_invite_tokens
                SET revoked_at = :occurred_at
                WHERE event_id = :event_id AND revoked_at IS NULL
                """
            ),
            {"event_id": event_id, "occurred_at": occurred_at},
        )

    async def delete_draft(self, event_id: UUID, *, expected_revision: int) -> bool:
        deleted = (
            await self._session.execute(
                text(
                    """
                    DELETE FROM talaqi.events
                    WHERE id = :event_id AND revision = :expected_revision
                      AND status = 'draft'
                    RETURNING id
                    """
                ),
                {"event_id": event_id, "expected_revision": expected_revision},
            )
        ).scalar_one_or_none()
        return deleted is not None

    @staticmethod
    def _parameters(event: Event, references: EventReferences) -> dict[str, object]:
        return {
            "id": event.id,
            "ownership_type": event.ownership_type,
            "club_id": event.club_id,
            "owner_user_id": event.owner_user_id,
            "title": event.title,
            "description": event.description,
            "category_id": references.category_id,
            "country_id": references.country_id,
            "city_id": references.city_id,
            "start_at": event.start_at,
            "end_at": event.end_at,
            "time_zone": event.time_zone,
            "capacity": event.capacity,
            "visibility": event.visibility,
            "status": event.status,
            "registration_method": event.registration_method,
            "cash_expiry_minutes": event.cash_expiry_minutes,
            "cancellation_cutoff_minutes": event.cancellation_cutoff_minutes,
            "district": event.district,
            "public_meeting_area": event.public_meeting_area,
            "exact_address": event.exact_address,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "exact_venue_is_public": event.exact_venue_is_public,
            "cover_media_id": event.cover_media_id,
            "revision": event.revision,
            "published_at": event.published_at,
            "cancelled_at": event.cancelled_at,
            "completed_at": event.completed_at,
            "suspended_at": event.suspended_at,
            "suspension_reason": event.suspension_reason,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }


__all__ = ["EventRepository"]
