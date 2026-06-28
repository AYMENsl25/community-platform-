from app.scripts.seed_dev import SEED_STATEMENTS


def test_seed_statements_are_idempotent() -> None:
    assert SEED_STATEMENTS
    assert all("ON CONFLICT" in statement for statement in SEED_STATEMENTS)


def test_seed_contains_minimum_demo_records() -> None:
    joined_sql = "\n".join(SEED_STATEMENTS)

    assert "organizer@communiti.local" in joined_sql
    assert "member@communiti.local" in joined_sql
    assert "riyadh-trailheads" in joined_sql
    assert "communiti-ai-lab" in joined_sql
    assert "sunrise-edge-walk" in joined_sql
    assert "ai-builders-night" in joined_sql
