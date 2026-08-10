from __future__ import annotations

from fastapi import APIRouter, Request

from talaqi.dashboard.repository import DashboardRepository
from talaqi.dashboard.schemas import MemberDashboardResponse, OrganizerDashboardResponse
from talaqi.identity.dependencies import CurrentPrincipal, DatabaseSession
from talaqi.platform import ApiError
from talaqi.profiles.runtime import build_registration_eligibility_service

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/me/dashboard", response_model=MemberDashboardResponse)
async def member_dashboard(
    request: Request, principal: CurrentPrincipal, session: DatabaseSession
) -> MemberDashboardResponse:
    data = await DashboardRepository(session).member(principal.user_id)
    settings = request.app.state.settings_factory()
    capabilities = await build_registration_eligibility_service(session, settings).evaluate(
        principal
    )
    data["profile_blockers"] = capabilities.blockers
    return MemberDashboardResponse.model_validate(data)


@router.get("/organizer/dashboard", response_model=OrganizerDashboardResponse)
async def organizer_dashboard(
    principal: CurrentPrincipal, session: DatabaseSession
) -> OrganizerDashboardResponse:
    data = await DashboardRepository(session).organizer(principal.user_id)
    if not data["clubs"] and not data["events"]:
        raise ApiError(code="forbidden", message_key="errors.forbidden", status_code=403)
    return OrganizerDashboardResponse.model_validate(data)


__all__ = ["router"]
