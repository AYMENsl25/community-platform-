from __future__ import annotations

from datetime import datetime
from uuid import UUID

from talaqi.audit import AuditService
from talaqi.identity.models import AuthPrincipal
from talaqi.outbox.models import OperationalOutboxEvent
from talaqi.outbox.repository import OutboxRepository
from talaqi.platform import ApiError
from talaqi.security import can_access_admin, can_moderate


class OutboxOperationsService:
    def __init__(self, repository: OutboxRepository, audit: AuditService) -> None:
        self._repository = repository
        self._audit = audit

    async def list(
        self, principal: AuthPrincipal, *, status: str | None, event_type: str | None, limit: int
    ) -> tuple[OperationalOutboxEvent, ...]:
        can_access_admin(principal)
        return await self._repository.list_operational(
            status=status, event_type=event_type, limit=limit
        )

    async def get(self, principal: AuthPrincipal, event_id: UUID) -> OperationalOutboxEvent:
        can_access_admin(principal)
        event = await self._repository.get_operational(event_id)
        if event is None:
            raise ApiError(
                code="outbox_event_not_found", message_key="errors.not_found", status_code=404
            )
        return event

    async def retry(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        *,
        reason: str,
        now: datetime,
        request_id: UUID,
    ) -> OperationalOutboxEvent:
        can_access_admin(principal)
        can_moderate(
            principal, has_active_mfa=await self._repository.has_active_mfa(principal.user_id)
        )
        normalized = reason.strip()
        if len(normalized) < 3:
            raise ApiError(code="invalid_reason", message_key="errors.validation", status_code=422)
        before = await self._repository.get_operational(event_id)
        if before is None:
            raise ApiError(
                code="outbox_event_not_found", message_key="errors.not_found", status_code=404
            )
        updated = await self._repository.retry_permanent_failure(event_id, now=now)
        if updated is None:
            raise ApiError(
                code="outbox_retry_conflict", message_key="errors.conflict", status_code=409
            )
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="admin",
            action="outbox.retry",
            target_type="outbox_event",
            target_id=event_id,
            reason=normalized,
            safe_before={
                "status": before.status,
                "attempt_count": before.attempt_count,
                "last_error_code": before.last_error_code,
                "event_type": before.event_type,
            },
            safe_after={
                "status": updated.status,
                "attempt_count": updated.attempt_count,
                "event_type": updated.event_type,
            },
            request_id=request_id,
        )
        return updated


__all__ = ["OutboxOperationsService"]
