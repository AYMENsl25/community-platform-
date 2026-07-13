from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from talaqi.db.identifiers import generate_uuid7, validate_uuid7


def test_generated_application_identifier_is_uuid_version_7() -> None:
    identifier = generate_uuid7()

    assert isinstance(identifier, UUID)
    assert identifier.version == 7
    assert identifier.variant == "specified in RFC 4122"


def test_uuid7_validation_accepts_uuid_objects_and_canonical_strings() -> None:
    identifier = generate_uuid7()

    assert validate_uuid7(identifier) is identifier
    assert validate_uuid7(str(identifier)) == identifier


@pytest.mark.parametrize("value", [str(uuid4()), "not-a-uuid", "", None])
def test_uuid7_validation_rejects_non_uuid7_values(value: object) -> None:
    with pytest.raises(ValueError, match="UUIDv7"):
        validate_uuid7(value)
