from __future__ import annotations

import json
from dataclasses import asdict
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit.models import AuditEvent, NewAuditEvent


class AuditRepositoryProtocol(Protocol):
    async def create_audit_event(self, event: NewAuditEvent) -> AuditEvent: ...


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_audit_event(self, event: NewAuditEvent) -> AuditEvent:
        params = asdict(event)
        params["safe_before"] = (
            json.dumps(event.safe_before) if event.safe_before is not None else None
        )
        params["safe_after"] = (
            json.dumps(event.safe_after) if event.safe_after is not None else None
        )
        params["ip_prefix"] = str(event.ip_prefix) if event.ip_prefix is not None else None

        row = (
            (
                await self._session.execute(
                    text(
                        """
                        INSERT INTO talaqi.audit_events (
                            id, actor_user_id, actor_kind, action, target_type, target_id,
                            reason, safe_before, safe_after, request_id, ip_prefix
                        ) VALUES (
                            :id, :actor_user_id, :actor_kind, :action, :target_type, :target_id,
                            :reason, CAST(:safe_before AS jsonb), CAST(:safe_after AS jsonb),
                            :request_id, CAST(:ip_prefix AS inet)
                        )
                        RETURNING created_at
                        """
                    ),
                    params,
                )
            )
            .mappings()
            .one()
        )
        return AuditEvent(
            **asdict(event),
            created_at=row["created_at"],
        )
