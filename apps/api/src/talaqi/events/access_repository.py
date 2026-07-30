from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.events.access_models import (
    EventAudienceProjection,
    ManagerVenueProjection,
    PrivateLinkRecord,
)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int, Decimal)):
        return float(value)
    raise TypeError("venue coordinate must be numeric")


def _projection(row: Mapping[str, object]) -> EventAudienceProjection:
    return EventAudienceProjection(
        id=cast(UUID, row["id"]),
        title=cast(str, row["title"]),
        description=cast(str, row["description"]),
        country_code=cast(str, row["country_code"]).strip(),
        city_slug=cast(str, row["city_slug"]),
        category_slug=cast(str, row["category_slug"]),
        start_at=cast(datetime, row["start_at"]),
        end_at=cast(datetime, row["end_at"]),
        time_zone=cast(str, row["time_zone"]),
        price_type="free" if row["registration_method"] == "free" else "cash",
        district=cast(str | None, row["district"]),
        public_meeting_area=cast(str | None, row["public_meeting_area"]),
        exact_address=cast(str | None, row["projected_exact_address"]),
        latitude=_optional_float(row["projected_latitude"]),
        longitude=_optional_float(row["projected_longitude"]),
        capacity=cast(int | None, row["capacity"]),
        available_places=(
            None
            if row["capacity"] is None
            else max(0, cast(int, row["capacity"]) - cast(int, row["reserved"]))
        ),
        cover_storage_key=cast(str | None, row["cover_storage_key"]),
        club_slug=cast(str | None, row["club_slug"]),
        club_name=cast(str | None, row["club_name"]),
        organizer_display_name=cast(str | None, row["organizer_display_name"]),
        is_saved=cast(bool, row["is_saved"]),
        registration_state=cast(
            Literal["confirmed", "cash_pending", "waitlisted", "cancelled", "expired"] | None,
            row["registration_state"],
        ),
    )


class EventAccessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_link(
        self,
        *,
        link_id: UUID,
        event_id: UUID,
        actor_id: UUID,
        token_hash: bytes,
        expires_at: datetime,
        now: datetime,
        rotate: bool,
    ) -> PrivateLinkRecord | None:
        active = (
            await self._session.execute(
                text(
                    """
                    SELECT id
                    FROM talaqi.event_invite_tokens
                    WHERE event_id = :event_id
                      AND revoked_at IS NULL
                      AND (expires_at IS NULL OR expires_at > :now)
                    FOR UPDATE
                    """
                ),
                {"event_id": event_id, "now": now},
            )
        ).scalar_one_or_none()
        if active is not None and not rotate:
            return None
        await self._session.execute(
            text(
                """
                UPDATE talaqi.event_invite_tokens
                SET revoked_at = :now
                WHERE event_id = :event_id AND revoked_at IS NULL
                RETURNING id
                """
            ),
            {"event_id": event_id, "now": now},
        )
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        INSERT INTO talaqi.event_invite_tokens (
                            id, event_id, token_hash, created_by_user_id, expires_at, created_at
                        ) VALUES (
                            :id, :event_id, CAST(:token_hash AS bytea), :actor_id,
                            :expires_at, :now
                        )
                        RETURNING id, event_id, expires_at, revoked_at
                        """
                    ),
                    {
                        "id": link_id,
                        "event_id": event_id,
                        "token_hash": token_hash,
                        "actor_id": actor_id,
                        "expires_at": expires_at,
                        "now": now,
                    },
                )
            )
            .mappings()
            .one()
        )
        return PrivateLinkRecord(
            id=cast(UUID, row["id"]),
            event_id=cast(UUID, row["event_id"]),
            expires_at=cast(datetime, row["expires_at"]),
            revoked_at=cast(datetime | None, row["revoked_at"]),
        )

    async def revoke_links(self, event_id: UUID, *, now: datetime) -> bool:
        result = await self._session.execute(
            text(
                """
                UPDATE talaqi.event_invite_tokens
                SET revoked_at = :now
                WHERE event_id = :event_id AND revoked_at IS NULL
                RETURNING id
                """
            ),
            {"event_id": event_id, "now": now},
        )
        return result.scalars().first() is not None

    async def resolve_link(self, token_hash: bytes, *, now: datetime) -> UUID | None:
        event_id = (
            await self._session.execute(
                text(
                    """
                    SELECT invite.event_id
                    FROM talaqi.event_invite_tokens AS invite
                    JOIN talaqi.events AS event ON event.id = invite.event_id
                    LEFT JOIN talaqi.clubs AS club ON club.id = event.club_id
                    WHERE invite.token_hash = CAST(:token_hash AS bytea)
                      AND invite.revoked_at IS NULL
                      AND (invite.expires_at IS NULL OR invite.expires_at > :now)
                      AND event.status = 'published'
                      AND event.visibility = 'private_link'
                      AND event.suspended_at IS NULL
                      AND (
                          event.ownership_type <> 'club'
                          OR (club.status = 'published' AND club.suspended_at IS NULL)
                      )
                    FOR UPDATE OF invite
                    """
                ),
                {"token_hash": token_hash, "now": now},
            )
        ).scalar_one_or_none()
        if event_id is None:
            return None
        await self._session.execute(
            text(
                """
                UPDATE talaqi.event_invite_tokens
                SET last_used_at = :now
                WHERE token_hash = CAST(:token_hash AS bytea)
                """
            ),
            {"token_hash": token_hash, "now": now},
        )
        return cast(UUID, event_id)

    async def project_manager_venue(self, event_id: UUID) -> ManagerVenueProjection | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT exact_address, latitude, longitude
                        FROM talaqi.events
                        WHERE id = :event_id AND suspended_at IS NULL
                        """
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return ManagerVenueProjection(
            exact_address=cast(str | None, row["exact_address"]),
            latitude=_optional_float(row["latitude"]),
            longitude=_optional_float(row["longitude"]),
        )

    async def project(
        self,
        event_id: UUID,
        *,
        caller_id: UUID | None,
        visibility: Literal["public", "private_link"],
        now: datetime,
    ) -> EventAudienceProjection | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT event.id, event.title, event.description,
                               country.code AS country_code, city.slug AS city_slug,
                               category.slug AS category_slug, event.start_at, event.end_at,
                               event.time_zone, event.registration_method, event.district,
                               event.public_meeting_area,
                               event.capacity,
                               cover.storage_key AS cover_storage_key,
                               club.slug AS club_slug, club.name AS club_name,
                               coalesce(owner_profile.display_name, club.name)
                                   AS organizer_display_name,
                               registration.state::text AS registration_state,
                               EXISTS (
                                   SELECT 1 FROM talaqi.saved_events AS saved
                                   WHERE saved.event_id = event.id AND saved.user_id = :caller_id
                               ) AS is_saved,
                               (
                                   SELECT count(*)::integer
                                   FROM talaqi.registrations AS held
                                   WHERE held.event_id = event.id AND held.seat_held
                               ) AS reserved,
                               CASE WHEN (
                                   event.exact_venue_is_public
                                   OR (
                                       :caller_id IS NOT NULL
                                       AND (
                                           (
                                               event.ownership_type = 'independent'
                                               AND event.owner_user_id = :caller_id
                                           )
                                           OR (
                                               event.ownership_type = 'club'
                                               AND (
                                                   club.owner_user_id = :caller_id
                                                   OR EXISTS (
                                                       SELECT 1
                                                       FROM talaqi.club_memberships AS membership
                                                       WHERE membership.club_id = event.club_id
                                                         AND membership.user_id = :caller_id
                                                         AND membership.role IN ('owner', 'admin')
                                                   )
                                               )
                                           )
                                           OR registration.state = 'confirmed'
                                           OR (
                                               registration.state = 'cash_pending'
                                               AND registration.cash_expires_at > :now
                                           )
                                       )
                                   )
                               ) THEN event.exact_address ELSE NULL END
                                   AS projected_exact_address,
                               CASE WHEN (
                                   event.exact_venue_is_public
                                   OR (
                                       :caller_id IS NOT NULL
                                       AND (
                                           (
                                               event.ownership_type = 'independent'
                                               AND event.owner_user_id = :caller_id
                                           )
                                           OR (
                                               event.ownership_type = 'club'
                                               AND (
                                                   club.owner_user_id = :caller_id
                                                   OR EXISTS (
                                                       SELECT 1
                                                       FROM talaqi.club_memberships AS membership
                                                       WHERE membership.club_id = event.club_id
                                                         AND membership.user_id = :caller_id
                                                         AND membership.role IN ('owner', 'admin')
                                                   )
                                               )
                                           )
                                           OR registration.state = 'confirmed'
                                           OR (
                                               registration.state = 'cash_pending'
                                               AND registration.cash_expires_at > :now
                                           )
                                       )
                                   )
                               ) THEN event.latitude ELSE NULL END AS projected_latitude,
                               CASE WHEN (
                                   event.exact_venue_is_public
                                   OR (
                                       :caller_id IS NOT NULL
                                       AND (
                                           (
                                               event.ownership_type = 'independent'
                                               AND event.owner_user_id = :caller_id
                                           )
                                           OR (
                                               event.ownership_type = 'club'
                                               AND (
                                                   club.owner_user_id = :caller_id
                                                   OR EXISTS (
                                                       SELECT 1
                                                       FROM talaqi.club_memberships AS membership
                                                       WHERE membership.club_id = event.club_id
                                                         AND membership.user_id = :caller_id
                                                         AND membership.role IN ('owner', 'admin')
                                                   )
                                               )
                                           )
                                           OR registration.state = 'confirmed'
                                           OR (
                                               registration.state = 'cash_pending'
                                               AND registration.cash_expires_at > :now
                                           )
                                       )
                                   )
                               ) THEN event.longitude ELSE NULL END AS projected_longitude
                        FROM talaqi.events AS event
                        JOIN talaqi.countries AS country ON country.id = event.country_id
                        JOIN talaqi.cities AS city ON city.id = event.city_id
                        JOIN talaqi.categories AS category ON category.id = event.category_id
                        LEFT JOIN talaqi.clubs AS club ON club.id = event.club_id
                        LEFT JOIN talaqi.profiles AS owner_profile
                            ON owner_profile.user_id = event.owner_user_id
                        LEFT JOIN talaqi.media_assets AS cover ON cover.id = event.cover_media_id
                            AND cover.status = 'verified'
                        LEFT JOIN LATERAL (
                            SELECT member_registration.state,
                                   member_registration.cash_expires_at
                            FROM talaqi.registrations AS member_registration
                            WHERE member_registration.event_id = event.id
                              AND member_registration.user_id = :caller_id
                            ORDER BY member_registration.created_at DESC,
                                     member_registration.id DESC
                            LIMIT 1
                        ) AS registration ON true
                        WHERE event.id = :event_id
                          AND event.status = 'published'
                          AND event.visibility = CAST(:visibility AS talaqi.event_visibility)
                          AND event.suspended_at IS NULL
                          AND (
                              event.ownership_type <> 'club'
                              OR (club.status = 'published' AND club.suspended_at IS NULL)
                          )
                        """
                    ),
                    {
                        "event_id": event_id,
                        "caller_id": caller_id,
                        "visibility": visibility,
                        "now": now,
                    },
                )
            )
            .mappings()
            .one_or_none()
        )
        return _projection(cast(Mapping[str, object], row)) if row is not None else None


__all__ = ["EventAccessRepository"]
