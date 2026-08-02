"""Activate the registration state machine and idempotent transition history.

Revision ID: 0009_registration_state_machine
Revises: 0008_event_publishing
Create Date: 2026-08-02
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0009_registration_state_machine"
down_revision: str | None = "0008_event_publishing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STRICT_SEAT_STATE = """
(state = 'confirmed' AND seat_held AND confirmed_at IS NOT NULL
    AND waitlist_sequence IS NULL AND cash_expires_at IS NULL
    AND cancelled_at IS NULL AND expired_at IS NULL)
OR (state = 'cash_pending' AND seat_held AND method = 'cash_organizer_confirmed'
    AND cash_expires_at IS NOT NULL AND waitlist_sequence IS NULL
    AND confirmed_at IS NULL AND cancelled_at IS NULL AND expired_at IS NULL)
OR (state = 'waitlisted' AND NOT seat_held AND waitlist_sequence IS NOT NULL
    AND cash_expires_at IS NULL AND confirmed_at IS NULL
    AND cancelled_at IS NULL AND expired_at IS NULL)
OR (state = 'cancelled' AND NOT seat_held AND cancelled_at IS NOT NULL
    AND waitlist_sequence IS NULL AND cash_expires_at IS NULL AND expired_at IS NULL)
OR (state = 'expired' AND NOT seat_held AND method = 'cash_organizer_confirmed'
    AND expired_at IS NOT NULL AND cash_expires_at IS NOT NULL
    AND cash_expires_at <= expired_at AND waitlist_sequence IS NULL
    AND confirmed_at IS NULL AND cancelled_at IS NULL)
"""

_BASELINE_SEAT_STATE = """
(state = 'confirmed' AND seat_held AND confirmed_at IS NOT NULL AND waitlist_sequence IS NULL)
OR (state = 'cash_pending' AND seat_held AND method = 'cash_organizer_confirmed'
    AND cash_expires_at IS NOT NULL AND waitlist_sequence IS NULL)
OR (state = 'waitlisted' AND NOT seat_held AND waitlist_sequence IS NOT NULL)
OR (state = 'cancelled' AND NOT seat_held AND cancelled_at IS NOT NULL)
OR (state = 'expired' AND NOT seat_held
    AND method = 'cash_organizer_confirmed' AND expired_at IS NOT NULL)
"""


def _replace_seat_state(expression: str) -> None:
    op.execute(
        sa.text("ALTER TABLE talaqi.registrations DROP CONSTRAINT ck_registrations_seat_state")
    )
    op.execute(
        sa.text(
            "ALTER TABLE talaqi.registrations "
            "ADD CONSTRAINT ck_registrations_seat_state "
            f"CHECK ({expression})"  # noqa: S608 -- migration-owned constant expression
        )
    )


def upgrade() -> None:
    op.add_column(
        "registration_transitions",
        sa.Column(
            "command_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("uuidv7()"),
        ),
        schema="talaqi",
    )
    op.add_column(
        "registration_transitions",
        sa.Column(
            "command_hash",
            sa.LargeBinary(),
            nullable=False,
            server_default=sa.text("decode(repeat('00', 32), 'hex')"),
        ),
        schema="talaqi",
    )
    op.add_column(
        "registration_transitions",
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        schema="talaqi",
    )
    op.alter_column(
        "registration_transitions",
        "command_id",
        server_default=None,
        schema="talaqi",
    )
    op.alter_column(
        "registration_transitions",
        "command_hash",
        server_default=None,
        schema="talaqi",
    )
    op.alter_column(
        "registration_transitions",
        "occurred_at",
        server_default=None,
        schema="talaqi",
    )

    op.execute(
        sa.text(
            "ALTER TABLE talaqi.registration_transitions "
            "ADD CONSTRAINT ck_registration_transitions_command_hash "
            "CHECK (octet_length(command_hash) = 32)"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE talaqi.registration_transitions "
            "ADD CONSTRAINT ck_registration_transitions_actor_shape "
            "CHECK ((actor_kind = 'system' AND actor_user_id IS NULL) "
            "OR (actor_kind <> 'system' AND actor_user_id IS NOT NULL))"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE talaqi.registration_transitions "
            "ADD CONSTRAINT ck_registration_transitions_reason_length "
            "CHECK (length(reason_code) BETWEEN 1 AND 80)"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE talaqi.registration_transitions "
            "ADD CONSTRAINT uq_registration_transitions_command_id UNIQUE (command_id)"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE talaqi.registrations "
            "ADD CONSTRAINT ck_registrations_waitlist_sequence_positive "
            "CHECK (waitlist_sequence IS NULL OR waitlist_sequence > 0)"
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE talaqi.registrations
            SET cash_expires_at = expired_at
            WHERE state = 'expired' AND cash_expires_at IS NULL
            """
        )
    )
    _replace_seat_state(_STRICT_SEAT_STATE)


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    _replace_seat_state(_BASELINE_SEAT_STATE)
    op.drop_constraint(
        "ck_registrations_waitlist_sequence_positive",
        "registrations",
        schema="talaqi",
    )
    op.drop_constraint(
        "uq_registration_transitions_command_id",
        "registration_transitions",
        schema="talaqi",
        type_="unique",
    )
    op.drop_constraint(
        "ck_registration_transitions_reason_length",
        "registration_transitions",
        schema="talaqi",
    )
    op.drop_constraint(
        "ck_registration_transitions_actor_shape",
        "registration_transitions",
        schema="talaqi",
    )
    op.drop_constraint(
        "ck_registration_transitions_command_hash",
        "registration_transitions",
        schema="talaqi",
    )
    op.drop_column("registration_transitions", "occurred_at", schema="talaqi")
    op.drop_column("registration_transitions", "command_hash", schema="talaqi")
    op.drop_column("registration_transitions", "command_id", schema="talaqi")
