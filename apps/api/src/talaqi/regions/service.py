from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from talaqi.regions.models import Category, City, Country, DeadlineObligation, RegionPolicy
from talaqi.regions.repository import RegionRepository


class RegionPolicyService:
    def __init__(self, repository: RegionRepository) -> None:
        self._repository = repository

    async def get(self, country_code: str) -> RegionPolicy:
        return await self._repository.get_policy(country_code)

    async def list_countries(self) -> tuple[Country, ...]:
        return await self._repository.list_countries()

    async def list_cities(self, country_code: str | None = None) -> tuple[City, ...]:
        return await self._repository.list_cities(country_code)

    async def list_categories(self) -> tuple[Category, ...]:
        return await self._repository.list_categories()

    @staticmethod
    def validate_deadlines(
        policy: RegionPolicy,
        *,
        event_start: datetime,
        obligations: Iterable[DeadlineObligation] = (),
    ) -> None:
        if event_start.tzinfo is None or event_start.utcoffset() is None:
            raise ValueError("event start must be timezone-aware")
        for label, default, bounds in (
            ("cash", policy.cash_default_minutes, policy.cash_bounds),
            ("cancellation", policy.cancellation_default_minutes, policy.cancellation_bounds),
        ):
            lower, upper = bounds
            if lower < 0 or upper < 0 or lower > upper or not lower <= default <= upper:
                raise ValueError(f"{label} deadline bounds are invalid")
        for obligation in obligations:
            timestamps = (obligation.issued_at, obligation.deadline)
            if any(value.tzinfo is None or value.utcoffset() is None for value in timestamps):
                raise ValueError("active obligation timestamps must be timezone-aware")
            if obligation.issued_at > obligation.deadline:
                raise ValueError("active obligation duration cannot be negative")
            if obligation.deadline > event_start:
                raise ValueError("active obligation deadline cannot pass event start")
            if obligation.kind == "cash":
                duration = _whole_minutes(obligation.deadline - obligation.issued_at)
                if not policy.cash_bounds[0] <= duration <= policy.cash_bounds[1]:
                    raise ValueError("cash obligation falls outside proposed bounds")
            elif obligation.kind == "cancellation":
                duration = _whole_minutes(event_start - obligation.deadline)
                if not policy.cancellation_bounds[0] <= duration <= policy.cancellation_bounds[1]:
                    raise ValueError("cancellation obligation falls outside proposed bounds")
            else:
                raise ValueError("active obligation kind is unsupported")


def _whole_minutes(duration: timedelta) -> int:
    total_seconds = duration.total_seconds()
    if total_seconds < 0 or total_seconds % 60 != 0:
        raise ValueError("active obligation duration must be non-negative whole minutes")
    return int(total_seconds // 60)
