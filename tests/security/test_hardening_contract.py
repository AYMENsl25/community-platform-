from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THREAT_MODEL = ROOT / "docs" / "security" / "closed-beta-threat-model.md"


def test_threat_model_covers_every_closed_beta_boundary_and_required_review() -> None:
    model = THREAT_MODEL.read_text(encoding="utf-8")
    for boundary in (
        "public web boundary",
        "FastAPI application",
        "PostgreSQL authority",
        "object storage",
        "transactional outbox worker",
        "email adapter",
        "administrator operations",
        "CI/release path",
    ):
        assert boundary in model
    for review in (
        "Session theft",
        "Host-header",
        "IDOR",
        "Private-link",
        "polyglot upload",
        "Registration race",
        "stale lease",
        "Report abuse",
        "vulnerable dependency",
        "deleted identity",
    ):
        assert review in model


def test_security_exceptions_are_bounded_and_never_allow_high_or_critical_findings() -> None:
    model = THREAT_MODEL.read_text(encoding="utf-8")
    exception = model.split("## Security exception process", maxsplit=1)[1]
    assert "No high or critical finding may be accepted" in exception
    for required in (
        "finding ID",
        "affected asset",
        "exploit preconditions",
        "owner",
        "compensating control",
        "expiry date",
        "remediation trigger",
        "verification evidence",
    ):
        assert required in exception
    assert "Expired exceptions block release" in exception


def test_security_matrix_references_real_verification_paths() -> None:
    model = THREAT_MODEL.read_text(encoding="utf-8")
    referenced = (
        "apps/api/tests/identity",
        "apps/api/tests/security",
        "apps/api/tests/audit/test_authorization.py",
        "apps/api/tests/events/test_private_access.py",
        "apps/api/tests/media",
        "apps/api/tests/registrations",
        "apps/worker/tests",
        "tests/security",
    )
    for relative in referenced:
        assert relative in model
        assert (ROOT / relative).exists()
