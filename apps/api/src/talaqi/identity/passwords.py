from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
from functools import lru_cache
from importlib.resources import files

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type
from email_validator import EmailNotValidError, validate_email

from talaqi.platform import ApiError

_USERNAME = re.compile(r"^[a-z0-9_]{3,30}$", re.ASCII)


def _invalid_input() -> ApiError:
    return ApiError(
        code="invalid_credentials_input",
        message_key="errors.invalid_credentials_input",
        status_code=422,
    )


@lru_cache(maxsize=1)
def _packaged_denylist() -> tuple[str, ...]:
    resource = files("talaqi.identity").joinpath("password_denylist.sha256")
    values = tuple(
        line.strip() for line in resource.read_text(encoding="ascii").splitlines() if line
    )
    if any(len(value) != 64 or value != value.upper() for value in values):
        raise RuntimeError("password denylist contains an invalid digest")
    return values


class PasswordPolicy:
    def __init__(self, denied_digests: tuple[str, ...]) -> None:
        self._denied_digests = denied_digests

    @classmethod
    def from_package_resource(cls) -> PasswordPolicy:
        return cls(_packaged_denylist())

    def validate(self, password: str) -> str:
        if not 12 <= len(password) <= 128 or not password.strip():
            raise _invalid_input()
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest().upper()
        if any(hmac.compare_digest(digest, denied) for denied in self._denied_digests):
            raise _invalid_input()
        return password


class PasswordService:
    def __init__(self, policy: PasswordPolicy) -> None:
        self.policy = policy
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65_536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )

    async def hash(self, password: str) -> str:
        supplied = self.policy.validate(password)
        return await asyncio.to_thread(self._hasher.hash, supplied)

    async def verify(self, encoded: str, password: str) -> bool:
        try:
            return await asyncio.to_thread(self._hasher.verify, encoded, password)
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            return False


def normalize_email(value: str) -> str:
    try:
        validated = validate_email(value.strip(), check_deliverability=False)
        return (validated.ascii_email or validated.normalized).lower()
    except EmailNotValidError:
        raise _invalid_input() from None


def normalize_username(value: str) -> str:
    normalized = value.strip().lower()
    if _USERNAME.fullmatch(normalized) is None:
        raise _invalid_input()
    return normalized


def normalize_login_identifier(value: str) -> str | None:
    try:
        return normalize_email(value) if "@" in value else normalize_username(value)
    except ApiError:
        return None
