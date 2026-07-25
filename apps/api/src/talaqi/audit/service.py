from __future__ import annotations

import ipaddress
import json
import re
from collections.abc import Mapping
from ipaddress import IPv4Network, IPv6Network
from typing import Any, Final, cast
from uuid import UUID

from talaqi.audit.models import ActorKind, AuditEvent, NewAuditEvent
from talaqi.audit.repository import AuditRepositoryProtocol
from talaqi.db.identifiers import generate_uuid7

_ACTION_PATTERN: Final = re.compile(r"^[a-z0-9_.]+$")
_TARGET_TYPE_PATTERN: Final = re.compile(r"^[a-z0-9_]+$")
_ACTOR_KINDS: Final = frozenset({"member", "organizer", "admin", "system"})
_SECRET_KEY_PARTS: Final = frozenset(
    {"authorization", "cookie", "credential", "password", "secret", "token"}
)
_PRIVATE_KEYS: Final = frozenset(
    {"email", "exact_address", "latitude", "longitude", "phone", "phone_number"}
)
_MAX_METADATA_BYTES: Final = 16_384
_MAX_REASON_LENGTH: Final = 2_000


def _reject_sensitive_metadata(value: object) -> None:
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        for raw_key, item in mapping.items():
            if not isinstance(raw_key, str):
                raise ValueError("safe metadata keys must be strings")
            normalized = raw_key.lower().replace("-", "_")
            key_parts = frozenset(part for part in normalized.split("_") if part)
            if normalized in _PRIVATE_KEYS or key_parts & _SECRET_KEY_PARTS:
                raise ValueError("safe metadata contains a sensitive key")
            _reject_sensitive_metadata(item)
    elif isinstance(value, (list, tuple)):
        sequence = cast(list[object] | tuple[object, ...], value)
        for item in sequence:
            _reject_sensitive_metadata(item)


def _snapshot_metadata(
    value: Mapping[str, Any] | None,
    *,
    field_name: str,
) -> dict[str, Any] | None:
    if value is None:
        return None
    _reject_sensitive_metadata(value)
    try:
        serialized = json.dumps(
            value,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must be a JSON object") from error
    if len(serialized.encode("utf-8")) > _MAX_METADATA_BYTES:
        raise ValueError(f"{field_name} exceeds {_MAX_METADATA_BYTES} bytes")
    snapshot = json.loads(serialized)
    if not isinstance(snapshot, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return cast(dict[str, Any], snapshot)


def _validate_actor(actor_user_id: UUID | None, actor_kind: ActorKind) -> None:
    if actor_kind not in _ACTOR_KINDS:
        raise ValueError("invalid actor_kind")
    if actor_kind == "system" and actor_user_id is not None:
        raise ValueError("system audit events cannot have an actor_user_id")
    if actor_kind != "system" and actor_user_id is None:
        raise ValueError("non-system audit events require actor_user_id")


class AuditService:
    def __init__(self, repository: AuditRepositoryProtocol) -> None:
        self.repository = repository

    async def record(
        self,
        *,
        actor_user_id: UUID | None,
        actor_kind: ActorKind,
        action: str,
        target_type: str,
        target_id: UUID | None = None,
        reason: str | None = None,
        safe_before: Mapping[str, Any] | None = None,
        safe_after: Mapping[str, Any] | None = None,
        request_id: UUID | None = None,
        ip_prefix: IPv4Network | IPv6Network | str | None = None,
    ) -> AuditEvent:
        _validate_actor(actor_user_id, actor_kind)
        if _ACTION_PATTERN.fullmatch(action) is None:
            raise ValueError("invalid audit action")
        if _TARGET_TYPE_PATTERN.fullmatch(target_type) is None:
            raise ValueError("invalid audit target_type")

        normalized_reason = reason.strip() if reason is not None else None
        if normalized_reason == "":
            normalized_reason = None
        if normalized_reason is not None and len(normalized_reason) > _MAX_REASON_LENGTH:
            raise ValueError(f"audit reason exceeds {_MAX_REASON_LENGTH} characters")

        parsed_ip = None
        if ip_prefix is not None:
            parsed_ip = (
                ip_prefix
                if isinstance(ip_prefix, (IPv4Network, IPv6Network))
                else ipaddress.ip_network(ip_prefix)
            )

        event = NewAuditEvent(
            id=generate_uuid7(),
            actor_user_id=actor_user_id,
            actor_kind=actor_kind,
            action=action,
            target_type=target_type,
            target_id=target_id,
            reason=normalized_reason,
            safe_before=_snapshot_metadata(safe_before, field_name="safe_before"),
            safe_after=_snapshot_metadata(safe_after, field_name="safe_after"),
            request_id=request_id,
            ip_prefix=parsed_ip,
        )
        return await self.repository.create_audit_event(event)
