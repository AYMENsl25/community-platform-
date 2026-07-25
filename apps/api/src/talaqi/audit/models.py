from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from ipaddress import IPv4Network, IPv6Network
from typing import Any, Literal
from uuid import UUID

ActorKind = Literal["member", "organizer", "admin", "system"]


@dataclass(frozen=True, slots=True)
class NewAuditEvent:
    id: UUID
    actor_user_id: UUID | None
    actor_kind: ActorKind
    action: str
    target_type: str
    target_id: UUID | None
    reason: str | None
    safe_before: Mapping[str, Any] | None
    safe_after: Mapping[str, Any] | None
    request_id: UUID | None
    ip_prefix: IPv4Network | IPv6Network | None


@dataclass(frozen=True, slots=True)
class AuditEvent(NewAuditEvent):
    created_at: datetime
