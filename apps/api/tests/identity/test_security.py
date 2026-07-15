from __future__ import annotations

from datetime import UTC, datetime

import pytest
from talaqi.identity.passwords import PasswordPolicy, PasswordService
from talaqi.platform import ApiError

from .test_service import MemoryRepository, service_for


@pytest.mark.asyncio
async def test_missing_and_wrong_password_paths_each_run_one_argon2_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MemoryRepository()
    service = service_for(repository)
    calls: list[tuple[str, str]] = []
    original = service.passwords.verify

    async def counted(encoded: str, supplied: str) -> bool:
        calls.append((encoded, supplied))
        return await original(encoded, supplied)

    monkeypatch.setattr(service.passwords, "verify", counted)
    with pytest.raises(ApiError):
        await service.login("absent@example.com", "wrong password value", now=datetime.now(UTC))
    assert len(calls) == 1

    service.passwords = PasswordService(PasswordPolicy.from_package_resource())
    await service.register(
        email="user@example.com",
        password="correct horse battery",  # pragma: allowlist secret
        age_attested=True,
        terms_version="2026-07-11",
        privacy_version="2026-07-11",
    )
    calls.clear()
    original = service.passwords.verify
    monkeypatch.setattr(service.passwords, "verify", counted)
    with pytest.raises(ApiError):
        await service.login("user@example.com", "wrong password value", now=datetime.now(UTC))
    assert len(calls) == 1
