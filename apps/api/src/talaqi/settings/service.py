from __future__ import annotations

from uuid import UUID

from talaqi.audit import AuditService
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.security import can_access_admin, can_moderate
from talaqi.settings.models import FEATURE_FLAGS, FeatureFlag, PlatformSetting
from talaqi.settings.repository import PlatformSettingsRepository


def _missing() -> ApiError:
    return ApiError(code="setting_not_found", message_key="errors.not_found", status_code=404)


class PlatformSettingsService:
    def __init__(
        self,
        repository: PlatformSettingsRepository,
        audit: AuditService | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit

    async def enabled(self, key: FeatureFlag) -> bool:
        if key not in FEATURE_FLAGS:
            raise ValueError("unsupported feature flag")
        setting = await self._repository.get_flag(key)
        if setting is None:
            raise RuntimeError(f"required feature flag is missing: {key}")
        return setting.enabled

    async def require_enabled(self, key: FeatureFlag) -> None:
        if not await self.enabled(key):
            raise ApiError(
                code="feature_disabled",
                message_key="errors.feature_disabled",
                status_code=403,
            )

    async def list_flags(self, principal: AuthPrincipal) -> tuple[PlatformSetting, ...]:
        can_access_admin(principal)
        settings = await self._repository.list_flags()
        if len(settings) != len(FEATURE_FLAGS):
            raise RuntimeError("required feature flag configuration is incomplete")
        return settings

    async def preview(
        self,
        principal: AuthPrincipal,
        key: FeatureFlag,
        *,
        enabled: bool,
        revision: int,
    ) -> tuple[PlatformSetting, PlatformSetting]:
        await self._require_mfa_admin(principal)
        current = await self._repository.get_flag(key)
        if current is None:
            raise _missing()
        if current.revision != revision:
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        return current, PlatformSetting(
            key=current.key,
            enabled=enabled,
            revision=current.revision + (enabled != current.enabled),
        )

    async def update(
        self,
        principal: AuthPrincipal,
        key: FeatureFlag,
        *,
        enabled: bool,
        revision: int,
        reason: str,
        request_id: UUID,
    ) -> PlatformSetting:
        await self._require_mfa_admin(principal)
        normalized_reason = reason.strip()
        if len(normalized_reason) < 3:
            raise ApiError(code="invalid_reason", message_key="errors.validation", status_code=422)
        current = await self._repository.get_flag(key, for_update=True)
        if current is None:
            raise _missing()
        if current.revision != revision:
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        if current.enabled == enabled:
            raise ApiError(code="no_changes", message_key="errors.validation", status_code=422)
        updated = await self._repository.update_flag(
            key,
            enabled=enabled,
            expected_revision=revision,
            actor_user_id=principal.user_id,
        )
        if updated is None:
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        if self._audit is None:
            raise RuntimeError("feature flag updates require audit service")
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="admin",
            action="settings.feature_flag.update",
            target_type="platform_setting",
            target_id=None,
            reason=normalized_reason,
            safe_before={
                "key": current.key,
                "enabled": current.enabled,
                "revision": current.revision,
            },
            safe_after={
                "key": updated.key,
                "enabled": updated.enabled,
                "revision": updated.revision,
            },
            request_id=request_id,
        )
        return updated

    async def _require_mfa_admin(self, principal: AuthPrincipal) -> None:
        can_access_admin(principal)
        can_moderate(
            principal,
            has_active_mfa=await self._repository.has_active_mfa(principal.user_id),
        )


__all__ = ["PlatformSettingsService"]
