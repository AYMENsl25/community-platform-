from __future__ import annotations

import pytest
from talaqi.localization.service import resolve_locale


@pytest.mark.parametrize(
    ("profile", "explicit", "accept_language", "regional_default", "expected"),
    [
        ("ar", "tr", "fr", "en", "ar"),
        (None, "tr-TR", "fr", "en", "tr"),
        (None, None, "de;q=1, fr-FR;q=0.7, ar;q=0.9", "tr", "ar"),
        (None, None, "tr;q=0, fr;q=0.8", "ar", "fr"),
        (None, None, "*;q=1, de;q=.9", "ar-DZ", "ar"),
        (None, None, "not a locale, fr;q=bogus", "xx", "en"),
    ],
)
def test_resolve_locale_uses_the_approved_precedence(
    profile: str | None,
    explicit: str | None,
    accept_language: str | None,
    regional_default: str | None,
    expected: str,
) -> None:
    assert resolve_locale(profile, explicit, accept_language, regional_default) == expected


def test_accept_language_uses_weight_then_header_order() -> None:
    assert resolve_locale(None, None, "fr;q=0.8, tr;q=0.8, ar;q=0.7", None) == "fr"


@pytest.mark.parametrize(
    "value",
    ["fr;q=1.1", "ar;q=-1", "tr;q=", "en;q=0", "en;q=0.000", "en;q=nan"],
)
def test_accept_language_ignores_invalid_or_zero_weight_entries(value: str) -> None:
    assert resolve_locale(None, None, value, "tr") == "tr"
