from __future__ import annotations

from collections.abc import Mapping
from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.settings.models import FEATURE_FLAGS, FeatureFlag, PlatformSetting


def _setting(row: Mapping[str, object]) -> PlatformSetting:
    return PlatformSetting(
        key=cast(FeatureFlag, row["key"]),
        enabled=cast(bool, row["enabled"]),
        revision=cast(int, row["revision"]),
    )


class PlatformSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_active_mfa(self, user_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM talaqi.user_mfa_factors
                        WHERE user_id = :user_id
                          AND verified_at IS NOT NULL
                          AND disabled_at IS NULL
                    )
                    """
                ),
                {"user_id": user_id},
            )
        )

    async def list_flags(self) -> tuple[PlatformSetting, ...]:
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT key, (value #>> '{}')::boolean AS enabled, revision
                    FROM talaqi.platform_settings
                    WHERE key = ANY(:keys)
                    ORDER BY key
                    """
                ),
                {"keys": list(FEATURE_FLAGS)},
            )
        ).mappings()
        return tuple(_setting(cast(Mapping[str, object], row)) for row in rows)

    async def get_flag(
        self, key: FeatureFlag, *, for_update: bool = False
    ) -> PlatformSetting | None:
        locking = " FOR UPDATE" if for_update else ""
        row = (
            (
                await self._session.execute(
                    text(
                        "SELECT key, (value #>> '{}')::boolean AS enabled, revision "
                        "FROM talaqi.platform_settings WHERE key = :key" + locking
                    ),
                    {"key": key},
                )
            )
            .mappings()
            .one_or_none()
        )
        return _setting(cast(Mapping[str, object], row)) if row is not None else None

    async def update_flag(
        self,
        key: FeatureFlag,
        *,
        enabled: bool,
        expected_revision: int,
        actor_user_id: UUID,
    ) -> PlatformSetting | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        UPDATE talaqi.platform_settings
                        SET value = to_jsonb(CAST(:enabled AS boolean)),
                            revision = revision + 1,
                            updated_by_user_id = :actor_user_id
                        WHERE key = :key AND revision = :expected_revision
                        RETURNING key, (value #>> '{}')::boolean AS enabled, revision
                        """
                    ),
                    {
                        "key": key,
                        "enabled": enabled,
                        "expected_revision": expected_revision,
                        "actor_user_id": actor_user_id,
                    },
                )
            )
            .mappings()
            .one_or_none()
        )
        return _setting(cast(Mapping[str, object], row)) if row is not None else None


__all__ = ["PlatformSettingsRepository"]
