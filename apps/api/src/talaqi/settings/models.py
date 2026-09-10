from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FeatureFlag = Literal[
    "features.member_reports_enabled",
    "features.organizer_announcements_enabled",
    "features.independent_event_creation_enabled",
]

FEATURE_FLAGS: tuple[FeatureFlag, ...] = (
    "features.member_reports_enabled",
    "features.organizer_announcements_enabled",
    "features.independent_event_creation_enabled",
)


@dataclass(frozen=True, slots=True)
class PlatformSetting:
    key: FeatureFlag
    enabled: bool
    revision: int


__all__ = ["FEATURE_FLAGS", "FeatureFlag", "PlatformSetting"]
