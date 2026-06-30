"""baseline existing SQL schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-30
"""

from collections.abc import Iterator
from pathlib import Path

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def _split_sql_statements(sql: str) -> Iterator[str]:
    statement: list[str] = []
    index = 0
    in_single_quote = False
    in_dollar_quote = False

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if not in_dollar_quote and char == "'" and next_char != "'":
            in_single_quote = not in_single_quote
            statement.append(char)
        elif not in_single_quote and sql[index : index + 2] == "$$":
            in_dollar_quote = not in_dollar_quote
            statement.append("$$")
            index += 1
        elif char == ";" and not in_single_quote and not in_dollar_quote:
            candidate = "".join(statement).strip()
            if candidate and candidate.upper() not in {"BEGIN", "COMMIT"}:
                yield candidate
            statement = []
        else:
            statement.append(char)
        index += 1

    candidate = "".join(statement).strip()
    if candidate:
        yield candidate


def upgrade() -> None:
    schema_path = (
        Path(__file__).resolve().parents[1] / "sql" / "0001_initial_schema.sql"
    )
    bind = op.get_bind()
    for statement in _split_sql_statements(schema_path.read_text(encoding="utf-8")):
        bind.exec_driver_sql(statement)


def downgrade() -> None:
    raise NotImplementedError("Downgrade the baseline schema manually from backups.")
