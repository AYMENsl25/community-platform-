from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from talaqi.db.metadata import Base, metadata


def test_metadata_uses_the_talaqi_schema_and_shared_declarative_base() -> None:
    assert metadata.schema == "talaqi"
    assert Base.metadata is metadata


def test_metadata_generates_deterministic_constraint_and_index_names() -> None:
    parents = Table(
        "metadata_test_parents",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("slug", String, unique=True),
    )
    children = Table(
        "metadata_test_children",
        metadata,
        Column("id", Integer, primary_key=True),
        Column(
            "parent_id",
            ForeignKey(parents.c.id),  # pyright: ignore[reportUnknownArgumentType]
            nullable=False,
        ),
        Column("score", Integer, CheckConstraint("score > 0", name="positive_score")),
    )
    index = Index(None, children.c.parent_id, children.c.score)

    assert parents.primary_key.name == "pk_metadata_test_parents"
    unique_constraint = next(
        constraint for constraint in parents.constraints if isinstance(constraint, UniqueConstraint)
    )
    assert unique_constraint.name == "uq_metadata_test_parents_slug"
    assert children.primary_key.name == "pk_metadata_test_children"
    foreign_key_constraint = next(iter(children.c.parent_id.foreign_keys)).constraint
    assert foreign_key_constraint is not None
    assert foreign_key_constraint.name == (
        "fk_metadata_test_children_parent_id_metadata_test_parents"
    )
    assert next(iter(children.c.score.constraints)).name == (
        "ck_metadata_test_children_positive_score"
    )
    assert index.name == "ix_metadata_test_children_parent_id_score"

    metadata.remove(children)
    metadata.remove(parents)
