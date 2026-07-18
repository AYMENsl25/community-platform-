from __future__ import annotations

import re
from typing import Literal, cast

type LocaleCode = Literal["en", "tr", "fr", "ar"]

_SUPPORTED_LOCALES = frozenset({"en", "tr", "fr", "ar"})
_LANGUAGE_RANGE = re.compile(r"^[A-Za-z]{2}(?:-[A-Za-z0-9]{2,8})*$")
_QUALITY = re.compile(r"^(?:0(?:\.\d{0,3})?|1(?:\.0{0,3})?|\.\d{1,3})$")


def _normalize_locale(value: str | None) -> LocaleCode | None:
    if value is None:
        return None
    candidate = value.strip()
    if _LANGUAGE_RANGE.fullmatch(candidate) is None:
        return None
    primary = candidate.split("-", maxsplit=1)[0].lower()
    if primary not in _SUPPORTED_LOCALES:
        return None
    return cast(LocaleCode, primary)


def _request_locale(accept_language: str | None) -> LocaleCode | None:
    if not accept_language:
        return None
    weighted: list[tuple[float, int, LocaleCode]] = []
    for position, entry in enumerate(accept_language.split(",")):
        sections = [section.strip() for section in entry.split(";")]
        locale = _normalize_locale(sections[0])
        if locale is None:
            continue
        quality = 1.0
        valid = True
        seen_quality = False
        for parameter in sections[1:]:
            name, separator, raw_value = parameter.partition("=")
            if (
                separator != "="
                or name.strip().lower() != "q"
                or seen_quality
                or _QUALITY.fullmatch(raw_value.strip()) is None
            ):
                valid = False
                break
            seen_quality = True
            quality = float(raw_value.strip())
        if valid and quality > 0:
            weighted.append((quality, position, locale))
    if not weighted:
        return None
    return min(weighted, key=lambda item: (-item[0], item[1]))[2]


def resolve_locale(
    profile: str | None,
    explicit: str | None,
    accept_language: str | None,
    regional_default: str | None,
) -> LocaleCode:
    """Resolve a supported locale using Talaqi's privacy-safe precedence."""

    return (
        _normalize_locale(profile)
        or _normalize_locale(explicit)
        or _request_locale(accept_language)
        or _normalize_locale(regional_default)
        or "en"
    )
