from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

FIXTURE_OWNER_ID = UUID("018f0000-0000-7000-8000-000000000001")
PUBLIC_CLUB_IDS = (
    UUID("018f0000-0000-7000-8000-000000000101"),
    UUID("018f0000-0000-7000-8000-000000000102"),
)
PUBLIC_EVENT_IDS = (
    UUID("018f0000-0000-7000-8000-000000000201"),
    UUID("018f0000-0000-7000-8000-000000000202"),
    UUID("018f0000-0000-7000-8000-000000000203"),
    UUID("018f0000-0000-7000-8000-000000000204"),
)

_DRAFT_CLUB_ID = UUID("018f0000-0000-7000-8000-000000000191")
_SUSPENDED_CLUB_ID = UUID("018f0000-0000-7000-8000-000000000192")
_DRAFT_EVENT_ID = UUID("018f0000-0000-7000-8000-000000000291")
_SUSPENDED_EVENT_ID = UUID("018f0000-0000-7000-8000-000000000292")
_PRIVATE_EVENT_ID = UUID("018f0000-0000-7000-8000-000000000293")
_UNUSABLE_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$Lpm/Lp7Pi4/BGiV5tCGoQg$"
    "yBSqOu3Mu/QL0TgL8EngAUcK6oI8W0ln7GNcBBaYHnE"  # pragma: allowlist secret
)
_UNSAFE_TARGET = "fixture seeding requires an explicit local development or test database"


@dataclass(frozen=True, slots=True)
class FixtureDatabaseTarget:
    host: str
    port: int
    database: str


def validate_fixture_target(
    environment: str, database_url: str | SecretStr | None
) -> FixtureDatabaseTarget:
    raw_url = (
        database_url.get_secret_value() if isinstance(database_url, SecretStr) else database_url
    )
    if environment not in {"development", "test"} or not raw_url:
        raise ValueError(_UNSAFE_TARGET)
    try:
        parsed = urlsplit(raw_url)
        port = parsed.port
    except ValueError:
        raise ValueError(_UNSAFE_TARGET) from None
    host = parsed.hostname
    database = parsed.path.removeprefix("/")
    safe_host = host in {"localhost", "127.0.0.1", "::1"}
    safe_test_name = environment != "test" or database.endswith("_test")
    if (
        parsed.scheme != "postgresql+asyncpg"
        or not safe_host
        or port is None
        or not database
        or parsed.path != f"/{database}"
        or parsed.query
        or parsed.fragment
        or not safe_test_name
        or database.lower() in {"postgres", "template0", "template1"}
    ):
        raise ValueError(_UNSAFE_TARGET)
    return FixtureDatabaseTarget(host=host, port=port, database=database)


async def seed_discovery_fixtures(session: AsyncSession) -> None:
    """Upsert the closed-beta discovery fixture set without committing the transaction."""
    await session.execute(
        text(
            """
            INSERT INTO talaqi.users (
                id, email, password_hash, status, email_verified_at,
                terms_version, privacy_version, age_attested_at,
                organizer_rules_version, community_rules_version
            ) VALUES (
                :id, 'discovery-fixture-owner@invalid.example', :password_hash,
                'active', '2030-01-01T00:00:00Z', 'fixture-v1', 'fixture-v1',
                '2030-01-01T00:00:00Z', 'fixture-v1', 'fixture-v1'
            )
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                status = EXCLUDED.status,
                email_verified_at = EXCLUDED.email_verified_at,
                terms_version = EXCLUDED.terms_version,
                privacy_version = EXCLUDED.privacy_version,
                age_attested_at = EXCLUDED.age_attested_at,
                organizer_rules_version = EXCLUDED.organizer_rules_version,
                community_rules_version = EXCLUDED.community_rules_version
            """
        ),
        {"id": FIXTURE_OWNER_ID, "password_hash": _UNUSABLE_PASSWORD_HASH},
    )
    await session.execute(
        text(
            """
            INSERT INTO talaqi.profiles (
                user_id, username, display_name, country_id, city_id, locale,
                time_zone, preferred_currency, profile_completed_at
            )
            SELECT :user_id, 'discovery_fixture', 'Talaqi Fixture Organizer',
                   country.id, city.id, 'en', city.time_zone, country.default_currency,
                   '2030-01-01T00:00:00Z'
            FROM talaqi.countries AS country
            JOIN talaqi.cities AS city ON city.country_id = country.id
            WHERE country.code = 'TR' AND city.slug = 'istanbul'
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                display_name = EXCLUDED.display_name,
                country_id = EXCLUDED.country_id,
                city_id = EXCLUDED.city_id,
                locale = EXCLUDED.locale,
                time_zone = EXCLUDED.time_zone,
                preferred_currency = EXCLUDED.preferred_currency,
                profile_completed_at = EXCLUDED.profile_completed_at
            """
        ),
        {"user_id": FIXTURE_OWNER_ID},
    )
    await _seed_clubs(session)
    await _seed_events(session)


async def _seed_clubs(session: AsyncSession) -> None:
    clubs = (
        (
            PUBLIC_CLUB_IDS[0],
            "istanbul-community",
            "Istanbul Community Club",
            "Friendly public gatherings across Istanbul.",
            "TR",
            "istanbul",
            "social",
            "published",
        ),
        (
            PUBLIC_CLUB_IDS[1],
            "algiers-community",
            "Algiers Community Club",
            "Open cultural and technology gatherings across Algiers.",
            "DZ",
            "algiers",
            "arts-culture",
            "published",
        ),
        (
            _DRAFT_CLUB_ID,
            "fixture-draft-club",
            "Fixture Draft Club",
            "This club must stay out of public discovery.",
            "TR",
            "istanbul",
            "games",
            "draft",
        ),
        (
            _SUSPENDED_CLUB_ID,
            "fixture-suspended-club",
            "Fixture Suspended Club",
            "This club must stay out of public discovery.",
            "DZ",
            "algiers",
            "technology",
            "suspended",
        ),
    )
    statement = text(
        """
        INSERT INTO talaqi.clubs (
            id, owner_user_id, slug, name, description, category_id,
            country_id, city_id, status, published_at, suspended_at, suspension_reason
        )
        SELECT :id, :owner_id, :slug, :name, :description, category.id,
               country.id, city.id, CAST(:status AS talaqi.club_status),
               CASE WHEN :status = 'published' THEN '2030-01-01T00:00:00Z'::timestamptz END,
               CASE WHEN :status = 'suspended' THEN '2030-01-02T00:00:00Z'::timestamptz END,
               CASE WHEN :status = 'suspended' THEN 'fixture_safety_hold' END
        FROM talaqi.countries AS country
        JOIN talaqi.cities AS city ON city.country_id = country.id
        JOIN talaqi.categories AS category ON category.slug = :category
        WHERE country.code = :country AND city.slug = :city
        ON CONFLICT (id) DO UPDATE SET
            owner_user_id = EXCLUDED.owner_user_id,
            slug = EXCLUDED.slug,
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            category_id = EXCLUDED.category_id,
            country_id = EXCLUDED.country_id,
            city_id = EXCLUDED.city_id,
            status = EXCLUDED.status,
            published_at = EXCLUDED.published_at,
            suspended_at = EXCLUDED.suspended_at,
            suspension_reason = EXCLUDED.suspension_reason
        """
    )
    for identifier, slug, name, description, country, city, category, status in clubs:
        await session.execute(
            statement,
            {
                "id": identifier,
                "owner_id": FIXTURE_OWNER_ID,
                "slug": slug,
                "name": name,
                "description": description,
                "country": country,
                "city": city,
                "category": category,
                "status": status,
            },
        )


async def _seed_events(session: AsyncSession) -> None:
    events = (
        (
            PUBLIC_EVENT_IDS[0],
            PUBLIC_CLUB_IDS[0],
            "Istanbul Weekend Run",
            "sports",
            "TR",
            "istanbul",
            "free",
            "public",
            "published",
            "2035-04-12T07:00:00Z",
            "Europe/Istanbul",
            "Kadikoy",
            "Waterfront meeting point",
        ),
        (
            PUBLIC_EVENT_IDS[1],
            PUBLIC_CLUB_IDS[0],
            "Istanbul Technology Meetup",
            "technology",
            "TR",
            "istanbul",
            "cash_organizer_confirmed",
            "public",
            "published",
            "2035-04-19T15:00:00Z",
            "Europe/Istanbul",
            "Sisli",
            "Metro exit meeting area",
        ),
        (
            PUBLIC_EVENT_IDS[2],
            PUBLIC_CLUB_IDS[1],
            "Algiers Culture Walk",
            "arts-culture",
            "DZ",
            "algiers",
            "free",
            "public",
            "published",
            "2035-05-03T09:00:00Z",
            "Africa/Algiers",
            "Casbah",
            "Main square meeting area",
        ),
        (
            PUBLIC_EVENT_IDS[3],
            PUBLIC_CLUB_IDS[1],
            "Algiers Games Evening",
            "games",
            "DZ",
            "algiers",
            "cash_organizer_confirmed",
            "public",
            "published",
            "2035-05-10T17:00:00Z",
            "Africa/Algiers",
            "Hydra",
            "Community center entrance",
        ),
        (
            _DRAFT_EVENT_ID,
            PUBLIC_CLUB_IDS[0],
            "Fixture Draft Event",
            "sports",
            "TR",
            "istanbul",
            "free",
            "public",
            "draft",
            "2035-06-01T10:00:00Z",
            "Europe/Istanbul",
            "Besiktas",
            "Draft meeting area",
        ),
        (
            _SUSPENDED_EVENT_ID,
            PUBLIC_CLUB_IDS[1],
            "Fixture Suspended Event",
            "technology",
            "DZ",
            "algiers",
            "free",
            "public",
            "suspended",
            "2035-06-08T10:00:00Z",
            "Africa/Algiers",
            "Hydra",
            "Suspended meeting area",
        ),
        (
            _PRIVATE_EVENT_ID,
            PUBLIC_CLUB_IDS[0],
            "Fixture Private Event",
            "games",
            "TR",
            "istanbul",
            "free",
            "private_link",
            "published",
            "2035-06-15T10:00:00Z",
            "Europe/Istanbul",
            "Fatih",
            "Private meeting area",
        ),
    )
    statement = text(
        """
        INSERT INTO talaqi.events (
            id, ownership_type, club_id, title, description, category_id,
            country_id, city_id, start_at, end_at, time_zone, capacity,
            visibility, status, registration_method, cash_expiry_minutes,
            cancellation_cutoff_minutes, district, public_meeting_area,
            exact_address, latitude, longitude, exact_venue_is_public,
            published_at, suspended_at, suspension_reason
        )
        SELECT :id, 'club', :club_id, :title,
               'Deterministic public discovery fixture event.', category.id,
               country.id, city.id, CAST(:start_at AS timestamptz),
               CAST(:start_at AS timestamptz) + interval '2 hours', :time_zone, 24,
               CAST(:visibility AS talaqi.event_visibility),
               CAST(:status AS talaqi.event_status),
               CAST(:registration_method AS talaqi.registration_method),
               CASE WHEN :registration_method = 'cash_organizer_confirmed' THEN 1440 END,
               1440, :district, :meeting_area,
               'Fixture exact address - never expose publicly', 41.008238, 28.978359, false,
               CASE WHEN :status = 'published' THEN '2030-01-01T00:00:00Z'::timestamptz END,
               CASE WHEN :status = 'suspended' THEN '2030-01-02T00:00:00Z'::timestamptz END,
               CASE WHEN :status = 'suspended' THEN 'fixture_safety_hold' END
        FROM talaqi.countries AS country
        JOIN talaqi.cities AS city ON city.country_id = country.id
        JOIN talaqi.categories AS category ON category.slug = :category
        WHERE country.code = :country AND city.slug = :city
        ON CONFLICT (id) DO UPDATE SET
            ownership_type = EXCLUDED.ownership_type,
            club_id = EXCLUDED.club_id,
            owner_user_id = NULL,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            category_id = EXCLUDED.category_id,
            country_id = EXCLUDED.country_id,
            city_id = EXCLUDED.city_id,
            start_at = EXCLUDED.start_at,
            end_at = EXCLUDED.end_at,
            time_zone = EXCLUDED.time_zone,
            capacity = EXCLUDED.capacity,
            visibility = EXCLUDED.visibility,
            status = EXCLUDED.status,
            registration_method = EXCLUDED.registration_method,
            cash_expiry_minutes = EXCLUDED.cash_expiry_minutes,
            cancellation_cutoff_minutes = EXCLUDED.cancellation_cutoff_minutes,
            district = EXCLUDED.district,
            public_meeting_area = EXCLUDED.public_meeting_area,
            exact_address = EXCLUDED.exact_address,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            exact_venue_is_public = EXCLUDED.exact_venue_is_public,
            published_at = EXCLUDED.published_at,
            suspended_at = EXCLUDED.suspended_at,
            suspension_reason = EXCLUDED.suspension_reason
        """
    )
    for row in events:
        (
            identifier,
            club_id,
            title,
            category,
            country,
            city,
            registration_method,
            visibility,
            status,
            start_at,
            time_zone,
            district,
            meeting_area,
        ) = row
        await session.execute(
            statement,
            {
                "id": identifier,
                "club_id": club_id,
                "title": title,
                "category": category,
                "country": country,
                "city": city,
                "registration_method": registration_method,
                "visibility": visibility,
                "status": status,
                "start_at": datetime.fromisoformat(start_at.replace("Z", "+00:00")),
                "time_zone": time_zone,
                "district": district,
                "meeting_area": meeting_area,
            },
        )


__all__ = [
    "FIXTURE_OWNER_ID",
    "PUBLIC_CLUB_IDS",
    "PUBLIC_EVENT_IDS",
    "FixtureDatabaseTarget",
    "seed_discovery_fixtures",
    "validate_fixture_target",
]
