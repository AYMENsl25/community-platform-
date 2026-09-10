from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from talaqi.security.logging import redact_sensitive

METRIC_CONTRACT: dict[str, tuple[str, ...]] = {
    "http_requests_total": ("method", "route", "status_class"),
    "http_request_duration_ms": ("method", "route"),
    "db_pool_saturation_ratio": (),
    "object_storage_capacity_ratio": (),
    "outbox_oldest_pending_seconds": ("event_type",),
    "outbox_failures_total": ("event_type", "failure_class"),
    "email_failures_total": ("failure_class",),
    "registration_transitions_total": ("from_state", "to_state"),
    "registration_expiry_total": ("result",),
    "waitlist_promotions_total": ("result",),
    "moderation_sla_breaches_total": ("priority",),
    "business_funnel_total": ("step", "region"),
    "invariant_violations_total": ("invariant",),
}

_SAFE_VALUE = re.compile(r"^[a-z0-9_./{}:-]{1,120}$")


def validate_metric(name: str, labels: Mapping[str, str]) -> None:
    expected = METRIC_CONTRACT.get(name)
    if expected is None or set(labels) != set(expected):
        raise ValueError("metric or label contract is unsupported")
    if any(not _SAFE_VALUE.fullmatch(value) for value in labels.values()):
        raise ValueError("metric labels must be bounded low-cardinality identifiers")


def emit_metric(
    logger: logging.Logger,
    name: str,
    value: int | float,
    labels: Mapping[str, str],
    *,
    trace_id: str | None = None,
    request_id: str | None = None,
    timestamp: datetime | None = None,
) -> None:
    validate_metric(name, labels)
    event = {
        "timestamp": (timestamp or datetime.now(UTC)).astimezone(UTC).isoformat(),
        "event": "metric.observed",
        "metric": name,
        "value": value,
        "labels": dict(labels),
        "trace_id": trace_id,
        "request_id": request_id,
    }
    logger.info(json.dumps(redact_sensitive(event), ensure_ascii=False, separators=(",", ":")))


@dataclass(frozen=True, slots=True)
class AlertRule:
    name: str
    metric: str
    threshold: float
    comparison: str

    def fires(self, sample: float) -> bool:
        return sample > self.threshold if self.comparison == "gt" else sample >= self.threshold


ALERT_RULES = (
    AlertRule("api_outage", "http_5xx_ratio", 0.05, "gt"),
    AlertRule("migration_failure", "migration_failures_total", 1, "gte"),
    AlertRule("stalled_queue", "outbox_oldest_pending_seconds", 300, "gt"),
    AlertRule("database_capacity", "db_pool_saturation_ratio", 0.85, "gt"),
    AlertRule("storage_capacity", "object_storage_capacity_ratio", 0.85, "gt"),
    AlertRule("critical_email_failure", "critical_email_failures_total", 1, "gte"),
    AlertRule("invariant_violation", "invariant_violations_total", 1, "gte"),
)


def exercise_alerts(samples: Mapping[str, float]) -> tuple[str, ...]:
    return tuple(rule.name for rule in ALERT_RULES if rule.fires(samples.get(rule.metric, 0)))


__all__ = ["ALERT_RULES", "METRIC_CONTRACT", "emit_metric", "exercise_alerts", "validate_metric"]
