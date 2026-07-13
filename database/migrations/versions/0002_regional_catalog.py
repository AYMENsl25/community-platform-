"""Seed the configurable launch-region catalog and policies.

Revision ID: 0002_regional_catalog
Revises: 0001_closed_beta_baseline
Create Date: 2026-07-14
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.util.concurrency import await_only
from talaqi.db.safety import validate_test_database_url

revision: str = "0002_regional_catalog"
down_revision: str | None = "0001_closed_beta_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _seed_sql() -> str:
    return """
    UPDATE talaqi.countries
    SET name_key = 'regions.country.tr'
    WHERE code = 'TR';

    UPDATE talaqi.countries
    SET name_key = 'regions.country.dz', default_locale = 'fr'
    WHERE code = 'DZ';

    UPDATE talaqi.cities AS city
    SET name_key = 'regions.city.istanbul'
    FROM talaqi.countries AS country
    WHERE city.country_id = country.id AND country.code = 'TR' AND city.slug = 'istanbul';

    UPDATE talaqi.cities AS city
    SET name_key = 'regions.city.algiers'
    FROM talaqi.countries AS country
    WHERE city.country_id = country.id AND country.code = 'DZ' AND city.slug = 'algiers';

    UPDATE talaqi.categories
    SET name_key = 'categories.sports', icon_key = 'sports', sort_order = 10, enabled = true
    WHERE slug = 'sports';

    UPDATE talaqi.categories
    SET name_key = 'categories.outdoors', icon_key = 'outdoors', sort_order = 50, enabled = true
    WHERE slug = 'outdoors';

    INSERT INTO talaqi.categories (slug, name_key, icon_key, sort_order, enabled)
    VALUES
        ('arts-culture', 'categories.arts_culture', 'arts-culture', 20, true),
        ('technology', 'categories.technology', 'technology', 30, true),
        ('language-exchange', 'categories.language_exchange', 'language-exchange', 40, true),
        ('games', 'categories.games', 'games', 60, true)
    ON CONFLICT (slug) DO UPDATE SET
        name_key = EXCLUDED.name_key,
        icon_key = EXCLUDED.icon_key,
        sort_order = EXCLUDED.sort_order,
        enabled = EXCLUDED.enabled;

    UPDATE talaqi.categories
    SET enabled = false
    WHERE slug IN ('education', 'culture', 'social', 'wellness');

    INSERT INTO talaqi.schema_revisions (revision, description)
    VALUES ('2026-07-14-regional-catalog', 'Launch regional catalog and policy defaults')
    ON CONFLICT (revision) DO UPDATE SET description = EXCLUDED.description;
    """


def _downgrade_sql() -> str:
    return """
    UPDATE talaqi.countries
    SET name_key = 'countries.tr'
    WHERE code = 'TR';

    UPDATE talaqi.countries
    SET name_key = 'countries.dz', default_locale = 'ar'
    WHERE code = 'DZ';

    UPDATE talaqi.cities AS city
    SET name_key = 'cities.istanbul'
    FROM talaqi.countries AS country
    WHERE city.country_id = country.id AND country.code = 'TR' AND city.slug = 'istanbul';

    UPDATE talaqi.cities AS city
    SET name_key = 'cities.algiers'
    FROM talaqi.countries AS country
    WHERE city.country_id = country.id AND country.code = 'DZ' AND city.slug = 'algiers';

    UPDATE talaqi.categories
    SET name_key = 'categories.sports', icon_key = 'ball', sort_order = 10, enabled = true
    WHERE slug = 'sports';

    UPDATE talaqi.categories
    SET name_key = 'categories.outdoors', icon_key = 'mountain', sort_order = 20, enabled = true
    WHERE slug = 'outdoors';

    UPDATE talaqi.categories
    SET enabled = true
    WHERE slug IN ('education', 'culture', 'social', 'wellness');

    DELETE FROM talaqi.categories
    WHERE slug IN ('arts-culture', 'technology', 'language-exchange', 'games');
    DELETE FROM talaqi.schema_revisions WHERE revision = '2026-07-14-regional-catalog';
    """


def _execute(script: str) -> None:
    if context.is_offline_mode():
        op.execute(sa.text(script))
        return
    driver_connection = op.get_bind().connection.driver_connection
    await_only(driver_connection.execute(script))


def upgrade() -> None:
    _execute(_seed_sql())


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    _execute(_downgrade_sql())
