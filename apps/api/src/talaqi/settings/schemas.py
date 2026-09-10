from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from talaqi.settings.models import FeatureFlag


class FeatureFlagResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    key: FeatureFlag
    enabled: bool
    revision: int


class FeatureFlagPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: list[FeatureFlagResponse]
    next_cursor: None = None


class FeatureFlagChangeRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    enabled: StrictBool
    revision: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=1_000)


class FeatureFlagPreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    current: FeatureFlagResponse
    proposed: FeatureFlagResponse
    changed: bool
    impact: Literal["blocks_new_mutations_only"] = "blocks_new_mutations_only"


class FeatureFlagUpdateResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    setting: FeatureFlagResponse
    status: Literal["updated"] = "updated"


__all__ = [
    "FeatureFlagChangeRequest",
    "FeatureFlagPageResponse",
    "FeatureFlagPreviewResponse",
    "FeatureFlagResponse",
    "FeatureFlagUpdateResponse",
]
