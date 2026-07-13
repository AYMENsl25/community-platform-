from __future__ import annotations

from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


def _all_column_names(constraint: Any, _table: Any) -> str:
    return "_".join(column.name for column in constraint.columns)


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(all_column_names)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
    "all_column_names": _all_column_names,
}

metadata = MetaData(schema="talaqi", naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata
