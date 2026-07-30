from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.identifiers import generate_uuid7

from .fixtures import app_for, complete_event_body, create_user

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.asyncio
async def test_published_event_constraint_keeps_capacity_optional(
    event_engine: AsyncEngine,
) -> None:
    async with event_engine.connect() as connection:
        definition = (
            await connection.execute(
                text(
                    """
                    SELECT pg_get_constraintdef(oid)
                    FROM pg_constraint
                    WHERE conrelid = 'talaqi.events'::regclass
                      AND conname = 'ck_events_published_fields'
                    """
                )
            )
        ).scalar_one()
    normalized = " ".join(definition.lower().split())
    assert "capacity is not null" not in normalized
    assert "registration_method is not null" in normalized
    assert "cancellation_cutoff_minutes is not null" in normalized


@pytest.mark.asyncio
async def test_downgrade_preserves_unlimited_published_events(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        created = await client.post(
            "/api/v1/events",
            json=complete_event_body(title="Unlimited migration round trip"),
            headers=owner.headers(idempotency_key=f"migration-{generate_uuid7()}"),
        )
    assert created.status_code == 201
    assert created.json()["capacity"] is None
    event_id = UUID(created.json()["id"])
    config = Config(str(ROOT / "alembic.ini"))
    try:
        await asyncio.to_thread(command.downgrade, config, "0007_moderation_priority")
        async with event_engine.connect() as connection:
            capacity = (
                await connection.execute(
                    text("SELECT capacity FROM talaqi.events WHERE id = :event_id"),
                    {"event_id": event_id},
                )
            ).scalar_one()
        assert capacity == 2147483647
    finally:
        await asyncio.to_thread(command.upgrade, config, "head")
