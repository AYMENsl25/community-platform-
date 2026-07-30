from __future__ import annotations

from uuid import UUID

from talaqi.clubs.repository import ClubRepositoryProtocol
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.security import can_edit_club


class ClubEventAccessService:
    """Public clubs-module boundary for event manager authorization."""

    def __init__(self, repository: ClubRepositoryProtocol) -> None:
        self._repository = repository

    async def require_event_manager(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        *,
        for_update: bool = False,
    ) -> None:
        club = await self._repository.get(club_id, for_update=for_update)
        if club is None:
            raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
        access = await self._repository.get_access(
            club.id,
            principal.user_id,
            for_update=for_update,
        )
        can_edit_club(principal, club, access)


__all__ = ["ClubEventAccessService"]
