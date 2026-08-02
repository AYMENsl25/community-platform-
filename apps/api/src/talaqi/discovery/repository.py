from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.discovery.models import (
    ClubCard,
    ClubPosition,
    DiscoveryFilters,
    DiscoveryPosition,
    EventCard,
    SearchPosition,
    SearchResult,
)

_SCORE = "CASE WHEN event.ownership_type = 'club' THEN 10 ELSE 0 END"
_PUBLIC_EVENT = (
    "event.status = 'published' AND event.visibility = 'public' AND event.suspended_at IS NULL"
)


def _event(row: Mapping[str, object]) -> EventCard:
    return EventCard(
        id=cast(UUID, row["id"]),
        title=cast(str, row["title"]),
        description=cast(str, row["description"]),
        country_code=cast(str, row["country_code"]).strip(),
        city_slug=cast(str, row["city_slug"]),
        category_slug=cast(str, row["category_slug"]),
        start_at=cast(datetime, row["start_at"]),
        end_at=cast(datetime, row["end_at"]),
        time_zone=cast(str, row["time_zone"]),
        ownership_type=cast(Literal["club", "independent"], row["ownership_type"]),
        cancellation_cutoff_minutes=cast(int, row["cancellation_cutoff_minutes"]),
        price_type="free" if row["registration_method"] == "free" else "cash",
        district=cast(str | None, row["district"]),
        public_meeting_area=cast(str | None, row["public_meeting_area"]),
        capacity=cast(int | None, row["capacity"]),
        available_places=(
            None
            if row["capacity"] is None
            else max(0, cast(int, row["capacity"]) - cast(int, row["reserved"]))
        ),
        cover_media_id=cast(UUID | None, row["cover_media_id"]),
        club_slug=cast(str | None, row["club_slug"]),
        club_name=cast(str | None, row["club_name"]),
        organizer_display_name=cast(str | None, row["organizer_display_name"]),
        is_saved=cast(bool, row["is_saved"]),
        registration_state=cast(str | None, row["registration_state"]),
        featured_score=cast(int, row["featured_score"]),
    )


def _club(row: Mapping[str, object]) -> ClubCard:
    return ClubCard(
        id=cast(UUID, row["id"]),
        slug=cast(str, row["slug"]),
        name=cast(str, row["name"]),
        name_key=cast(str, row["name_key"]),
        description=cast(str, row["description"]),
        country_code=cast(str, row["country_code"]).strip(),
        city_slug=cast(str, row["city_slug"]),
        category_slug=cast(str, row["category_slug"]),
        cover_media_id=cast(UUID | None, row["cover_media_id"]),
        member_count=cast(int, row["member_count"]),
    )


def _search(row: Mapping[str, object]) -> SearchResult:
    return SearchResult(
        kind=cast(str, row["kind"]),  # pyright: ignore[reportArgumentType]
        id=cast(UUID, row["id"]),
        slug=cast(str | None, row["slug"]),
        title=cast(str, row["title"]),
        description=cast(str, row["description"]),
        country_code=cast(str, row["country_code"]).strip(),
        city_slug=cast(str, row["city_slug"]),
        category_slug=cast(str, row["category_slug"]),
        start_at=cast(datetime | None, row["start_at"]),
        title_key=cast(str, row["title_key"]),
    )


class DiscoveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_events(
        self,
        filters: DiscoveryFilters,
        *,
        limit: int,
        after: DiscoveryPosition | None = None,
        caller_id: UUID | None = None,
        saved_only: bool = False,
        event_id: UUID | None = None,
        club_slug: str | None = None,
    ) -> list[EventCard]:
        conditions = [
            _PUBLIC_EVENT,
            "(event.ownership_type <> 'club' OR club.id IS NOT NULL)",
        ]
        params: dict[str, object] = {"limit": limit, "caller_id": caller_id}
        if event_id is not None:
            conditions.append("event.id = :event_id")
            params["event_id"] = event_id
        if club_slug is not None:
            conditions.append("club.slug = :club_slug")
            params["club_slug"] = club_slug
        if saved_only:
            if caller_id is None:
                return []
            conditions.append("saved.user_id IS NOT NULL")
        mappings = {
            "country": "country.code = :country",
            "city": "city.slug = :city",
            "category": "category.slug = :category",
            "search": (
                "to_tsvector('simple', event.title || ' ' || event.description) "
                "@@ plainto_tsquery('simple', :search)"
            ),
        }
        for field, condition in mappings.items():
            value = getattr(filters, field)
            if value is not None:
                conditions.append(condition)
                params[field] = value
        if filters.date_from is not None:
            conditions.append("event.start_at::date >= :date_from")
            params["date_from"] = filters.date_from
        if filters.date_to is not None:
            conditions.append("event.start_at::date <= :date_to")
            params["date_to"] = filters.date_to
        if filters.price == "free":
            conditions.append("event.registration_method = 'free'")
        elif filters.price == "cash":
            conditions.append("event.registration_method = 'cash_organizer_confirmed'")
        if after is not None:
            conditions.append(
                f"({_SCORE} < :after_score OR "
                f"({_SCORE} = :after_score AND event.start_at > :after_start) OR "
                f"({_SCORE} = :after_score AND event.start_at = :after_start "
                "AND event.id > :after_id))"
            )
            params.update(
                after_score=after.featured_score,
                after_start=after.start_at,
                after_id=after.id,
            )
        query = f"""
            SELECT event.id, event.title, event.description, country.code AS country_code,
                   city.slug AS city_slug, category.slug AS category_slug,
                   event.start_at, event.end_at, event.time_zone, event.ownership_type,
                   event.registration_method, event.cancellation_cutoff_minutes,
                   event.district, event.public_meeting_area,
                   event.capacity,
                   cover.id AS cover_media_id, club.slug AS club_slug,
                   club.name AS club_name,
                   coalesce(owner_profile.display_name, club.name) AS organizer_display_name,
                   {_SCORE} AS featured_score,
                   count(registration.id) FILTER (WHERE registration.seat_held) AS reserved,
                   bool_or(saved.user_id IS NOT NULL) AS is_saved,
                   max(registration.state::text) FILTER (
                       WHERE registration.user_id = :caller_id
                   ) AS registration_state
            FROM talaqi.events AS event
            JOIN talaqi.countries AS country ON country.id = event.country_id
            JOIN talaqi.cities AS city ON city.id = event.city_id
            JOIN talaqi.categories AS category ON category.id = event.category_id
            LEFT JOIN talaqi.clubs AS club ON club.id = event.club_id
                AND club.status = 'published' AND club.suspended_at IS NULL
            LEFT JOIN talaqi.profiles AS owner_profile
                ON owner_profile.user_id = event.owner_user_id
            LEFT JOIN talaqi.media_assets AS cover ON cover.id = event.cover_media_id
                AND cover.status = 'verified'
            LEFT JOIN talaqi.registrations AS registration ON registration.event_id = event.id
                AND registration.state IN ('confirmed', 'cash_pending', 'waitlisted')
            LEFT JOIN talaqi.saved_events AS saved ON saved.event_id = event.id
                AND saved.user_id = :caller_id
            WHERE {" AND ".join(conditions)}
            GROUP BY event.id, country.code, city.slug, category.slug, cover.id,
                     club.slug, club.name, owner_profile.display_name
            ORDER BY featured_score DESC, event.start_at ASC, event.id ASC
            LIMIT :limit
        """  # noqa: S608 -- fixed filter fragments; values are bound
        rows = (await self._session.execute(text(query), params)).mappings().all()
        return [_event(cast(Mapping[str, object], row)) for row in rows]

    async def get_event(self, event_id: UUID, *, caller_id: UUID | None = None) -> EventCard | None:
        events = await self.list_events(
            DiscoveryFilters(), limit=1, caller_id=caller_id, event_id=event_id
        )
        return events[0] if events else None

    async def list_clubs(
        self,
        filters: DiscoveryFilters,
        *,
        limit: int,
        slug: str | None = None,
        after: ClubPosition | None = None,
    ) -> list[ClubCard]:
        conditions = ["club.status = 'published'", "club.suspended_at IS NULL"]
        params: dict[str, object] = {"limit": limit}
        if slug is not None:
            conditions.append("club.slug = :slug")
            params["slug"] = slug
        if after is not None:
            conditions.append(
                "(lower(club.name) > :after_name OR "
                "(lower(club.name) = :after_name AND club.id > :after_id))"
            )
            params.update(after_name=after.name_key, after_id=after.id)
        for field, expression in (
            ("country", "country.code = :country"),
            ("city", "city.slug = :city"),
            ("category", "category.slug = :category"),
        ):
            value = getattr(filters, field)
            if value is not None:
                conditions.append(expression)
                params[field] = value
        if filters.search:
            conditions.append(
                "to_tsvector('simple', club.name || ' ' || coalesce(club.description, '')) "
                "@@ plainto_tsquery('simple', :search)"
            )
            params["search"] = filters.search
        rows = (
            (
                await self._session.execute(
                    text(
                        f"""SELECT club.id, club.slug, club.name, lower(club.name) AS name_key,
                               club.description,
                               country.code AS country_code, city.slug AS city_slug,
                               category.slug AS category_slug,
                               cover.id AS cover_media_id,
                               (
                                   SELECT count(*)::integer
                                   FROM talaqi.club_memberships AS membership
                                   WHERE membership.club_id = club.id
                               ) AS member_count
                        FROM talaqi.clubs AS club
                        JOIN talaqi.countries AS country ON country.id = club.country_id
                        JOIN talaqi.cities AS city ON city.id = club.city_id
                        JOIN talaqi.categories AS category ON category.id = club.category_id
                        LEFT JOIN talaqi.media_assets AS cover ON cover.id = club.cover_media_id
                            AND cover.status = 'verified'
                        WHERE {" AND ".join(conditions)}
                        ORDER BY lower(club.name) ASC, club.id ASC LIMIT :limit"""  # noqa: S608 -- fixed filter fragments
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        return [_club(cast(Mapping[str, object], row)) for row in rows]

    async def get_club(self, slug: str) -> ClubCard | None:
        clubs = await self.list_clubs(DiscoveryFilters(), limit=1, slug=slug)
        return clubs[0] if clubs else None

    async def search(
        self,
        filters: DiscoveryFilters,
        *,
        limit: int,
        after: SearchPosition | None = None,
    ) -> list[SearchResult]:
        params: dict[str, object] = {"limit": limit}
        event_conditions = [
            _PUBLIC_EVENT,
            "(event.ownership_type <> 'club' OR owning_club.id IS NOT NULL)",
        ]
        club_conditions = ["club.status = 'published'", "club.suspended_at IS NULL"]
        for field, event_sql, club_sql in (
            ("country", "country.code = :country", "country.code = :country"),
            ("city", "city.slug = :city", "city.slug = :city"),
            ("category", "category.slug = :category", "category.slug = :category"),
        ):
            value = getattr(filters, field)
            if value is not None:
                event_conditions.append(event_sql)
                club_conditions.append(club_sql)
                params[field] = value
        if filters.search is not None:
            event_conditions.append(
                "to_tsvector('simple', event.title || ' ' || event.description) "
                "@@ plainto_tsquery('simple', :search)"
            )
            club_conditions.append(
                "to_tsvector('simple', club.name || ' ' || coalesce(club.description, '')) "
                "@@ plainto_tsquery('simple', :search)"
            )
            params["search"] = filters.search
        after_sql = ""
        if after is not None:
            after_sql = """
                WHERE (result.title_key > :after_title OR
                       (result.title_key = :after_title AND result.kind > :after_kind) OR
                       (result.title_key = :after_title AND result.kind = :after_kind
                        AND result.id > :after_id))
            """
            params.update(
                after_title=after.title_key,
                after_kind=after.kind,
                after_id=after.id,
            )
        query = f"""
            WITH result AS (
                SELECT 'event'::text AS kind, event.id, NULL::text AS slug,
                       event.title, event.description, country.code AS country_code,
                       city.slug AS city_slug, category.slug AS category_slug,
                       event.start_at, lower(event.title) AS title_key
                FROM talaqi.events AS event
                JOIN talaqi.countries AS country ON country.id = event.country_id
                JOIN talaqi.cities AS city ON city.id = event.city_id
                JOIN talaqi.categories AS category ON category.id = event.category_id
                LEFT JOIN talaqi.clubs AS owning_club ON owning_club.id = event.club_id
                    AND owning_club.status = 'published'
                    AND owning_club.suspended_at IS NULL
                WHERE {" AND ".join(event_conditions)}
                UNION ALL
                SELECT 'club'::text AS kind, club.id, club.slug, club.name AS title,
                       club.description, country.code AS country_code,
                       city.slug AS city_slug, category.slug AS category_slug,
                       NULL::timestamptz AS start_at, lower(club.name) AS title_key
                FROM talaqi.clubs AS club
                JOIN talaqi.countries AS country ON country.id = club.country_id
                JOIN talaqi.cities AS city ON city.id = club.city_id
                JOIN talaqi.categories AS category ON category.id = club.category_id
                WHERE {" AND ".join(club_conditions)}
            )
            SELECT result.* FROM result
            {after_sql}
            ORDER BY result.title_key ASC, result.kind ASC, result.id ASC
            LIMIT :limit
        """  # noqa: S608 -- fixed filter fragments; values are bound
        rows = (await self._session.execute(text(query), params)).mappings().all()
        return [_search(cast(Mapping[str, object], row)) for row in rows]

    async def save_event(self, user_id: UUID, event_id: UUID) -> bool:
        public = await self._session.scalar(
            text(
                f"""WITH public_event AS MATERIALIZED (
                         SELECT event.id FROM talaqi.events AS event
                         LEFT JOIN talaqi.clubs AS owning_club
                           ON owning_club.id = event.club_id
                          AND owning_club.status = 'published'
                          AND owning_club.suspended_at IS NULL
                         WHERE event.id = :event_id AND {_PUBLIC_EVENT}
                           AND (event.ownership_type <> 'club' OR owning_club.id IS NOT NULL)
                     ), inserted AS (
                         INSERT INTO talaqi.saved_events (user_id, event_id)
                         SELECT :user_id, public_event.id FROM public_event
                         ON CONFLICT (user_id, event_id) DO NOTHING
                         RETURNING event_id
                     )
                     SELECT EXISTS (SELECT 1 FROM public_event)"""  # noqa: S608 -- fixed public predicate
            ),
            {"user_id": user_id, "event_id": event_id},
        )
        return bool(public)

    async def unsave_event(self, user_id: UUID, event_id: UUID) -> bool:
        public = await self._session.scalar(
            text(
                f"""WITH public_event AS MATERIALIZED (
                         SELECT event.id FROM talaqi.events AS event
                         LEFT JOIN talaqi.clubs AS owning_club
                           ON owning_club.id = event.club_id
                          AND owning_club.status = 'published'
                          AND owning_club.suspended_at IS NULL
                         WHERE event.id = :event_id AND {_PUBLIC_EVENT}
                           AND (event.ownership_type <> 'club' OR owning_club.id IS NOT NULL)
                     ), deleted AS (
                         DELETE FROM talaqi.saved_events AS saved
                         USING public_event
                         WHERE saved.user_id = :user_id
                           AND saved.event_id = public_event.id
                         RETURNING saved.event_id
                     )
                     SELECT EXISTS (SELECT 1 FROM public_event)"""  # noqa: S608 -- fixed public predicate
            ),
            {"user_id": user_id, "event_id": event_id},
        )
        return bool(public)


__all__ = ["DiscoveryRepository"]
