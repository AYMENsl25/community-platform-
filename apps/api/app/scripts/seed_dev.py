import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

SEED_STATEMENTS: tuple[str, ...] = (
    """
    INSERT INTO users (
      clerk_user_id,
      email,
      username,
      display_name,
      avatar_url,
      bio,
      city,
      country,
      is_onboarded
    )
    VALUES (
      'seed_user_organizer_1',
      'organizer@communiti.local',
      'seed_organizer',
      'COMMUNITI Organizer',
      '/placeholder-user.jpg',
      'Seed organizer used for local COMMUNITI development.',
      'Riyadh',
      'Saudi Arabia',
      true
    )
    ON CONFLICT (email) DO UPDATE SET
      clerk_user_id = EXCLUDED.clerk_user_id,
      username = EXCLUDED.username,
      display_name = EXCLUDED.display_name,
      avatar_url = EXCLUDED.avatar_url,
      bio = EXCLUDED.bio,
      city = EXCLUDED.city,
      country = EXCLUDED.country,
      is_onboarded = true
    """,
    """
    INSERT INTO users (
      clerk_user_id,
      email,
      username,
      display_name,
      avatar_url,
      bio,
      city,
      country,
      is_onboarded
    )
    VALUES (
      'seed_user_member_1',
      'member@communiti.local',
      'seed_member',
      'COMMUNITI Member',
      '/placeholder-user.jpg',
      'Seed member used for local registration and membership testing.',
      'Riyadh',
      'Saudi Arabia',
      true
    )
    ON CONFLICT (email) DO UPDATE SET
      clerk_user_id = EXCLUDED.clerk_user_id,
      username = EXCLUDED.username,
      display_name = EXCLUDED.display_name,
      avatar_url = EXCLUDED.avatar_url,
      bio = EXCLUDED.bio,
      city = EXCLUDED.city,
      country = EXCLUDED.country,
      is_onboarded = true
    """,
    """
    INSERT INTO user_preferences (
      user_id,
      interest_categories,
      interest_tags,
      preferred_city,
      max_distance_km
    )
    SELECT
      id,
      ARRAY['Outdoors', 'Technology', 'Wellness'],
      ARRAY['beginner-friendly', 'weekend', 'student-friendly'],
      'Riyadh',
      30
    FROM users
    WHERE email = 'member@communiti.local'
    ON CONFLICT (user_id) DO UPDATE SET
      interest_categories = EXCLUDED.interest_categories,
      interest_tags = EXCLUDED.interest_tags,
      preferred_city = EXCLUDED.preferred_city,
      max_distance_km = EXCLUDED.max_distance_km
    """,
    """
    WITH owner_user AS (
      SELECT id FROM users WHERE email = 'organizer@communiti.local'
    ), category AS (
      SELECT id FROM club_categories WHERE slug = 'outdoors'
    )
    INSERT INTO clubs (
      owner_id,
      category_id,
      name,
      slug,
      description,
      logo_url,
      cover_image_url,
      city,
      country,
      visibility,
      status
    )
    SELECT
      owner_user.id,
      category.id,
      'Riyadh Trailheads',
      'riyadh-trailheads',
      'Beginner-friendly hikes, outdoor trips, and weekend walks around Riyadh.',
      '/orgs/trailheads.png',
      '/experiences/sunrise-hike.png',
      'Riyadh',
      'Saudi Arabia',
      'public',
      'published'
    FROM owner_user, category
    ON CONFLICT (slug) DO UPDATE SET
      description = EXCLUDED.description,
      logo_url = EXCLUDED.logo_url,
      cover_image_url = EXCLUDED.cover_image_url,
      city = EXCLUDED.city,
      country = EXCLUDED.country,
      visibility = EXCLUDED.visibility,
      status = EXCLUDED.status
    """,
    """
    WITH owner_user AS (
      SELECT id FROM users WHERE email = 'organizer@communiti.local'
    ), category AS (
      SELECT id FROM club_categories WHERE slug = 'technology'
    )
    INSERT INTO clubs (
      owner_id,
      category_id,
      name,
      slug,
      description,
      logo_url,
      cover_image_url,
      city,
      country,
      visibility,
      status
    )
    SELECT
      owner_user.id,
      category.id,
      'COMMUNITI AI Lab',
      'communiti-ai-lab',
      'A practical community for AI builders, students, and product experiments.',
      '/placeholder-logo.png',
      '/experiences/book-club.png',
      'Riyadh',
      'Saudi Arabia',
      'public',
      'published'
    FROM owner_user, category
    ON CONFLICT (slug) DO UPDATE SET
      description = EXCLUDED.description,
      logo_url = EXCLUDED.logo_url,
      cover_image_url = EXCLUDED.cover_image_url,
      city = EXCLUDED.city,
      country = EXCLUDED.country,
      visibility = EXCLUDED.visibility,
      status = EXCLUDED.status
    """,
    """
    WITH owner_user AS (
      SELECT id FROM users WHERE email = 'organizer@communiti.local'
    )
    INSERT INTO club_members (club_id, user_id, role, status)
    SELECT clubs.id, owner_user.id, 'owner', 'active'
    FROM clubs, owner_user
    WHERE clubs.slug IN ('riyadh-trailheads', 'communiti-ai-lab')
    ON CONFLICT (club_id, user_id) DO UPDATE SET
      role = EXCLUDED.role,
      status = EXCLUDED.status,
      left_at = NULL
    """,
    """
    WITH member_user AS (
      SELECT id FROM users WHERE email = 'member@communiti.local'
    )
    INSERT INTO club_members (club_id, user_id, role, status)
    SELECT clubs.id, member_user.id, 'member', 'active'
    FROM clubs, member_user
    WHERE clubs.slug = 'riyadh-trailheads'
    ON CONFLICT (club_id, user_id) DO UPDATE SET
      role = EXCLUDED.role,
      status = EXCLUDED.status,
      left_at = NULL
    """,
    """
    WITH club AS (
      SELECT id FROM clubs WHERE slug = 'riyadh-trailheads'
    ), creator AS (
      SELECT id FROM users WHERE email = 'organizer@communiti.local'
    )
    INSERT INTO events (
      club_id,
      created_by,
      title,
      slug,
      description,
      event_type,
      starts_at,
      ends_at,
      timezone,
      location_name,
      address,
      city,
      country,
      lat,
      lng,
      capacity,
      price_amount,
      currency,
      status,
      requires_approval,
      cover_image_url
    )
    SELECT
      club.id,
      creator.id,
      'Sunrise Edge Walk',
      'sunrise-edge-walk',
      'A relaxed beginner-friendly sunrise walk with coffee after the route.',
      'outdoors',
      now() + interval '7 days',
      now() + interval '7 days 3 hours',
      'Asia/Riyadh',
      'Wadi Hanifah',
      'Wadi Hanifah, Riyadh',
      'Riyadh',
      'Saudi Arabia',
      24.6136,
      46.7152,
      12,
      0,
      'SAR',
      'published',
      false,
      '/experiences/sunrise-hike.png'
    FROM club, creator
    ON CONFLICT (club_id, slug) DO UPDATE SET
      description = EXCLUDED.description,
      starts_at = EXCLUDED.starts_at,
      ends_at = EXCLUDED.ends_at,
      location_name = EXCLUDED.location_name,
      address = EXCLUDED.address,
      capacity = EXCLUDED.capacity,
      price_amount = EXCLUDED.price_amount,
      status = EXCLUDED.status,
      cover_image_url = EXCLUDED.cover_image_url
    """,
    """
    WITH club AS (
      SELECT id FROM clubs WHERE slug = 'communiti-ai-lab'
    ), creator AS (
      SELECT id FROM users WHERE email = 'organizer@communiti.local'
    )
    INSERT INTO events (
      club_id,
      created_by,
      title,
      slug,
      description,
      event_type,
      starts_at,
      ends_at,
      timezone,
      location_name,
      address,
      city,
      country,
      capacity,
      price_amount,
      currency,
      status,
      requires_approval,
      cover_image_url
    )
    SELECT
      club.id,
      creator.id,
      'AI Builders Night',
      'ai-builders-night',
      'A hands-on evening for students and builders exploring AI products.',
      'technology',
      now() + interval '10 days',
      now() + interval '10 days 2 hours',
      'Asia/Riyadh',
      'Innovation Hub Riyadh',
      'Riyadh Innovation District',
      'Riyadh',
      'Saudi Arabia',
      30,
      25,
      'SAR',
      'published',
      false,
      '/experiences/book-club.png'
    FROM club, creator
    ON CONFLICT (club_id, slug) DO UPDATE SET
      description = EXCLUDED.description,
      starts_at = EXCLUDED.starts_at,
      ends_at = EXCLUDED.ends_at,
      location_name = EXCLUDED.location_name,
      address = EXCLUDED.address,
      capacity = EXCLUDED.capacity,
      price_amount = EXCLUDED.price_amount,
      status = EXCLUDED.status,
      cover_image_url = EXCLUDED.cover_image_url
    """,
    """
    WITH target_event AS (
      SELECT events.id
      FROM events
      JOIN clubs ON clubs.id = events.club_id
      WHERE clubs.slug = 'riyadh-trailheads'
        AND events.slug = 'sunrise-edge-walk'
    ), member_user AS (
      SELECT id FROM users WHERE email = 'member@communiti.local'
    )
    INSERT INTO event_registrations (event_id, user_id, status)
    SELECT target_event.id, member_user.id, 'confirmed'
    FROM target_event, member_user
    ON CONFLICT (event_id, user_id) DO UPDATE SET
      status = 'confirmed',
      cancelled_at = NULL,
      waitlist_position = NULL
    """,
    """
    WITH target_event AS (
      SELECT events.id
      FROM events
      JOIN clubs ON clubs.id = events.club_id
      WHERE clubs.slug = 'communiti-ai-lab'
        AND events.slug = 'ai-builders-night'
    ), member_user AS (
      SELECT id FROM users WHERE email = 'member@communiti.local'
    )
    INSERT INTO saved_events (user_id, event_id)
    SELECT member_user.id, target_event.id
    FROM member_user, target_event
    ON CONFLICT (user_id, event_id) DO NOTHING
    """,
)


async def seed_database(session: AsyncSession) -> None:
    if settings.environment == "production":
        raise RuntimeError("Refusing to run development seed data in production.")

    async with session.begin():
        for statement in SEED_STATEMENTS:
            await session.execute(text(statement))


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    logger.info("Seed data inserted successfully.")


if __name__ == "__main__":
    asyncio.run(main())
