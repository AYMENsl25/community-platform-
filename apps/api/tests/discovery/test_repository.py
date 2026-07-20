from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from talaqi.discovery.fixtures import PUBLIC_CLUB_IDS, PUBLIC_EVENT_IDS
from talaqi.discovery.models import DiscoveryFilters, DiscoveryPosition
from talaqi.discovery.repository import DiscoveryRepository

pytestmark = pytest.mark.asyncio


async def test_repository_filters_public_records_and_returns_coarse_venue_only(
    discovery_session: AsyncSession,
) -> None:
    repository = DiscoveryRepository(discovery_session)

    all_events = await repository.list_events(DiscoveryFilters(), limit=20)
    turkey = await repository.list_events(
        DiscoveryFilters(country="TR", city="istanbul", price="free"), limit=20
    )
    searched = await repository.list_events(DiscoveryFilters(search="weekend run"), limit=20)

    assert {event.id for event in all_events} == set(PUBLIC_EVENT_IDS)
    assert [event.title for event in turkey] == ["Istanbul Weekend Run"]
    assert [event.title for event in searched] == ["Istanbul Weekend Run"]
    rendered = repr(all_events).casefold()
    assert "fixture exact address" not in rendered
    assert "latitude" not in rendered
    assert "longitude" not in rendered
    assert all(event.available_places == 24 for event in all_events)


async def test_repository_cursor_predicate_matches_desc_score_asc_schedule(
    discovery_session: AsyncSession,
) -> None:
    repository = DiscoveryRepository(discovery_session)
    first_page = await repository.list_events(DiscoveryFilters(), limit=2)
    last = first_page[-1]

    second_page = await repository.list_events(
        DiscoveryFilters(),
        limit=20,
        after=DiscoveryPosition(last.featured_score, last.start_at, last.id),
    )

    assert not ({event.id for event in first_page} & {event.id for event in second_page})
    assert [event.id for event in first_page + second_page] == list(PUBLIC_EVENT_IDS)


async def test_exact_detail_queries_are_public_filtered(
    discovery_session: AsyncSession,
) -> None:
    repository = DiscoveryRepository(discovery_session)

    event = await repository.get_event(PUBLIC_EVENT_IDS[0])
    assert event is not None
    assert event.id == PUBLIC_EVENT_IDS[0]
    assert (
        await repository.get_event(
            PUBLIC_EVENT_IDS[0].__class__("018f0000-0000-7000-8000-000000000291")
        )
        is None
    )
    club = await repository.get_club("istanbul-community")
    assert club is not None
    assert club.slug == "istanbul-community"
    assert await repository.get_club("fixture-suspended-club") is None


async def test_save_rechecks_public_state_when_existing_save_conflicts(
    discovery_session: AsyncSession,
) -> None:
    repository = DiscoveryRepository(discovery_session)
    user_id = await discovery_session.scalar(
        text("SELECT id FROM talaqi.users WHERE email='discovery-fixture-owner@invalid.example'")
    )
    event_id = PUBLIC_EVENT_IDS[0]
    assert user_id is not None
    assert await repository.save_event(user_id, event_id) is True
    await discovery_session.execute(
        text("UPDATE talaqi.events SET visibility='private_link' WHERE id=:id"),
        {"id": event_id},
    )

    assert await repository.save_event(user_id, event_id) is False


async def test_club_event_query_is_constrained_before_limit(
    discovery_session: AsyncSession,
) -> None:
    repository = DiscoveryRepository(discovery_session)
    await discovery_session.execute(
        text(
            """INSERT INTO talaqi.events (
                   id,ownership_type,club_id,title,description,category_id,country_id,city_id,
                   start_at,end_at,time_zone,capacity,visibility,status,registration_method,
                   cancellation_cutoff_minutes,district,public_meeting_area,published_at
               )
               SELECT uuidv7(),source.ownership_type,source.club_id,'Other event ' || series.n,
                      source.description,source.category_id,source.country_id,source.city_id,
                      source.start_at - interval '4 years',source.end_at - interval '4 years',
                      source.time_zone,source.capacity,source.visibility,source.status,
                      source.registration_method,source.cancellation_cutoff_minutes,
                      source.district,source.public_meeting_area,source.published_at
               FROM talaqi.events AS source
               CROSS JOIN generate_series(1,55) AS series(n)
               WHERE source.id=:source"""
        ),
        {"source": PUBLIC_EVENT_IDS[0]},
    )
    target = await repository.list_events(
        DiscoveryFilters(), limit=1, club_slug="algiers-community"
    )

    assert len(target) == 1
    assert target[0].club_slug == "algiers-community"


async def test_club_cursor_key_is_exact_postgresql_lower_value(
    discovery_session: AsyncSession,
) -> None:
    await discovery_session.execute(
        text(
            """INSERT INTO talaqi.clubs (
                   id,owner_user_id,slug,name,description,category_id,country_id,city_id,
                   status,published_at
               )
               SELECT uuidv7(),club.owner_user_id,'unicode-istanbul-club',
                      'İstanbul Unicode Club','Unicode cursor fixture',club.category_id,
                      club.country_id,club.city_id,'published',clock_timestamp()
               FROM talaqi.clubs AS club WHERE club.id=:source"""
        ),
        {"source": PUBLIC_CLUB_IDS[0]},
    )
    clubs = await DiscoveryRepository(discovery_session).list_clubs(DiscoveryFilters(), limit=20)
    unicode_club = next(club for club in clubs if club.slug == "unicode-istanbul-club")
    sql_key = await discovery_session.scalar(
        text("SELECT lower(name) FROM talaqi.clubs WHERE id=:id"),
        {"id": unicode_club.id},
    )

    assert unicode_club.name_key == sql_key
    assert unicode_club.name_key != unicode_club.name.casefold()


async def test_club_owned_event_disappears_when_owning_club_is_suspended(
    discovery_session: AsyncSession,
) -> None:
    repository = DiscoveryRepository(discovery_session)
    user_id = await discovery_session.scalar(
        text("SELECT id FROM talaqi.users WHERE email='discovery-fixture-owner@invalid.example'")
    )
    assert user_id is not None
    assert await repository.save_event(user_id, PUBLIC_EVENT_IDS[0]) is True
    await discovery_session.execute(
        text(
            """UPDATE talaqi.clubs
               SET status='suspended',suspended_at=clock_timestamp(),
                   suspension_reason='test suspension'
               WHERE id=:id"""
        ),
        {"id": PUBLIC_CLUB_IDS[0]},
    )

    events = await repository.list_events(DiscoveryFilters(), limit=20)

    assert PUBLIC_EVENT_IDS[0] not in {event.id for event in events}
    assert PUBLIC_EVENT_IDS[1] not in {event.id for event in events}
    assert await repository.get_event(PUBLIC_EVENT_IDS[0]) is None
    search = await repository.search(DiscoveryFilters(search="istanbul"), limit=20)
    assert PUBLIC_EVENT_IDS[0] not in {item.id for item in search}
    assert PUBLIC_EVENT_IDS[1] not in {item.id for item in search}
    assert await repository.save_event(user_id, PUBLIC_EVENT_IDS[0]) is False
    assert await repository.unsave_event(user_id, PUBLIC_EVENT_IDS[0]) is False
