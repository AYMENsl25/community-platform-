"""Recovery-email handoff boundary.

The transactional outbox stores only identifiers. A delivery adapter reconstructs the
one-time public token immediately before provider delivery. Provider selection remains
deferred to the communications phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from talaqi.identity.tokens import AuthTokenCodec, AuthTokenKind


@dataclass(frozen=True, slots=True)
class RecoveryEmailIntent:
    user_id: UUID
    auth_token_id: UUID
    locale_hint: str
    template: AuthTokenKind


class RecoveryEmailLinkAdapter:
    def __init__(self, codec: AuthTokenCodec, web_public_url: str) -> None:
        self._codec = codec
        self._base = web_public_url.rstrip("/")

    def link(self, intent: RecoveryEmailIntent) -> str:
        token = self._codec.public_token(intent.auth_token_id, intent.template)
        path = "verify-email" if intent.template == "email_verification" else "reset-password"
        return f"{self._base}/{path}?token={token}"


__all__ = ["RecoveryEmailIntent", "RecoveryEmailLinkAdapter"]
