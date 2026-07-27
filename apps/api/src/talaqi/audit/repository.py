from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime
from ipaddress import IPv4Network, IPv6Network
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit.models import AuditEvent, NewAuditEvent


class AuditRepositoryProtocol(Protocol):
    async def create_audit_event(self, event: NewAuditEvent) -> AuditEvent: ...

    async def list_audit_events(
        self,
        *,
        target_type: str | None,
        target_id: UUID | None,
        actor_user_id: UUID | None,
        action: str | None,
        limit: int,
        after_created_at: datetime | None = None,
        after_id: UUID | None = None,
    ) -> list[AuditEvent]: ...


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

    async def list_audit_events(
        self,
        *,
        target_type: str | None,
        target_id: UUID | None,
        actor_user_id: UUID | None,
        action: str | None,
        limit: int,
        after_created_at: datetime | None = None,
        after_id: UUID | None = None,
    ) -> list[AuditEvent]:
        conditions: list[str] = []
        params: dict[str, object] = {"limit": limit}
        for field, value in (
            ("target_type", target_type),
            ("target_id", target_id),
            ("actor_user_id", actor_user_id),
            ("action", action),
        ):
            if value is not None:
                conditions.append(f"{field} = :{field}")
                params[field] = value
        if after_created_at is not None and after_id is not None:
            conditions.append(
                "(created_at < :after_created_at OR "
                "(created_at = :after_created_at AND id < :after_id))"
            )
            params.update(after_created_at=after_created_at, after_id=after_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = (
            (
                await self._session.execute(
                    text(
                        f"""
                        SELECT id, actor_user_id, actor_kind, action, target_type,
                               target_id, reason, safe_before, safe_after, request_id,
                               ip_prefix, created_at
                        FROM talaqi.audit_events
                        {where}
                        ORDER BY created_at DESC, id DESC
                        LIMIT :limit
                        """
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        return [self._audit_event(cast(Mapping[str, object], row)) for row in rows]

    @staticmethod
    def _audit_event(row: Mapping[str, object]) -> AuditEvent:
        return AuditEvent(
            id=cast(UUID, row["id"]),
            actor_user_id=cast(UUID | None, row["actor_user_id"]),
            actor_kind=cast(str, row["actor_kind"]),  # type: ignore[arg-type]
            action=cast(str, row["action"]),
            target_type=cast(str, row["target_type"]),
            target_id=cast(UUID | None, row["target_id"]),
            reason=cast(str | None, row["reason"]),
            safe_before=cast(Mapping[str, object] | None, row["safe_before"]),
            safe_after=cast(Mapping[str, object] | None, row["safe_after"]),
            request_id=cast(UUID | None, row["request_id"]),
            ip_prefix=cast(IPv4Network | IPv6Network | None, row["ip_prefix"]),
            created_at=cast(datetime, row["created_at"]),
        )
