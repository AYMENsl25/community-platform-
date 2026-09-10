from __future__ import annotations

import json
import logging
from io import StringIO
from pathlib import Path

import pytest
import yaml
from talaqi.telemetry import ALERT_RULES, METRIC_CONTRACT, emit_metric, exercise_alerts

ROOT = Path(__file__).resolve().parents[4]


def test_metric_contract_covers_beta_operations_without_personal_labels() -> None:
    required = {
        "http_requests_total",
        "http_request_duration_ms",
        "db_pool_saturation_ratio",
        "outbox_oldest_pending_seconds",
        "outbox_failures_total",
        "email_failures_total",
        "registration_transitions_total",
        "registration_expiry_total",
        "waitlist_promotions_total",
        "moderation_sla_breaches_total",
        "business_funnel_total",
        "invariant_violations_total",
    }
    assert required <= METRIC_CONTRACT.keys()
    forbidden = {"user_id", "email", "token", "event_id", "club_id", "request_id", "trace_id"}
    assert not forbidden.intersection(
        label for labels in METRIC_CONTRACT.values() for label in labels
    )


def test_metric_emission_is_exact_and_rejects_high_cardinality_or_unknown_labels() -> None:
    stream = StringIO()
    logger = logging.Logger("telemetry-test")
    logger.addHandler(logging.StreamHandler(stream))
    emit_metric(
        logger,
        "outbox_failures_total",
        1,
        {"event_type": "notification.email", "failure_class": "provider"},
    )
    event = json.loads(stream.getvalue())
    assert event["metric"] == "outbox_failures_total"
    assert event["labels"] == {"event_type": "notification.email", "failure_class": "provider"}
    with pytest.raises(ValueError, match="bounded low-cardinality"):
        emit_metric(
            logger,
            "outbox_failures_total",
            1,
            {"event_type": "person@example.test", "failure_class": "provider"},
        )
    with pytest.raises(ValueError, match="unsupported"):
        emit_metric(logger, "unknown_metric", 1, {})


def test_every_release_alert_fires_in_a_synthetic_exercise() -> None:
    samples = {
        "http_5xx_ratio": 0.2,
        "migration_failures_total": 1,
        "outbox_oldest_pending_seconds": 900,
        "db_pool_saturation_ratio": 0.95,
        "object_storage_capacity_ratio": 0.9,
        "critical_email_failures_total": 1,
        "invariant_violations_total": 1,
    }
    assert set(exercise_alerts(samples)) == {rule.name for rule in ALERT_RULES}
    assert exercise_alerts({}) == ()


def test_reviewable_alert_and_dashboard_artifacts_match_runtime_contract() -> None:
    alerts = yaml.safe_load((ROOT / "infrastructure/monitoring/alerts.yml").read_text("utf-8"))
    configured = {item["alert"] for group in alerts["groups"] for item in group["rules"]}
    assert configured == {rule.name for rule in ALERT_RULES}
    dashboard = json.loads((ROOT / "infrastructure/monitoring/dashboard.json").read_text("utf-8"))
    displayed = {metric for panel in dashboard["panels"] for metric in panel["metrics"]}
    assert METRIC_CONTRACT.keys() <= displayed | {"http_5xx_ratio"}
    assert dashboard["privacy"] == {"high_cardinality_labels": False, "personal_data": False}
