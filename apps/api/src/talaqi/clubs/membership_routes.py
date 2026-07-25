from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit import AuditRepository, AuditService
from talaqi.clubs.membership_models import JoinRequest, Membership
from talaqi.clubs.membership_repository import MembershipRepository
from talaqi.clubs.membership_schemas import (
    CloseClubRequest,
    DecisionRequest,
    JoinClubRequest,
    JoinClubResponse,
    JoinRequestPageResponse,
    JoinRequestResponse,
    MemberPageResponse,
    MemberResponse,
    OperationResponse,
    OwnershipTransferRequest,
    RoleChangeRequest,
)
from talaqi.clubs.membership_service import MembershipService
from talaqi.config import Settings
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.platform.errors import ErrorEnvelope, request_id_for
from talaqi.profiles.eligibility import CreationEligibilityService
from talaqi.profiles.repository import ProfileRepository
from talaqi.regions.repository import RegionRepository
from talaqi.regions.service import RegionPolicyService

router = APIRouter(prefix="/api/v1/clubs", tags=["club-memberships"])

_AUTH: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication required."}
_FORBIDDEN: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Capability, object authorization, or CSRF denied.",
}
_NOT_FOUND: dict[str, Any] = {"model": ErrorEnvelope, "description": "Resource not found."}
_CONFLICT: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Membership operation conflicted with current state.",
}


def _service(request: Request, session: AsyncSession) -> MembershipService:
    settings: Settings = request.app.state.settings_factory()
    eligibility = CreationEligibilityService(
        ProfileRepository(session),
        RegionPolicyService(RegionRepository(session)),
        current_terms_version=settings.current_terms_version,
        current_privacy_version=settings.current_privacy_version,
        current_organizer_rules_version=settings.current_organizer_rules_version,
        current_community_rules_version=settings.current_community_rules_version,
        admin_mfa_required=settings.admin_mfa_required,
    )
    return MembershipService(
        MembershipRepository(session),
        AuditService(AuditRepository(session)),
        eligibility,
    )


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"


def _member(value: Membership) -> MemberResponse:
    return MemberResponse(
        user_id=value.user_id,
        display_name=value.display_name,
        email=value.email,
        role=value.role,
        joined_at=value.joined_at,
    )


def _join_request(value: JoinRequest) -> JoinRequestResponse:
    return JoinRequestResponse(
        id=value.id,
        user_id=value.user_id,
        display_name=value.display_name,
        email=value.email,
        status=value.status,
        message=value.message,
        decision_reason=value.decision_reason,
        decided_at=value.decided_at,
        created_at=value.created_at,
    )


@router.post(
    "/{club_id:uuid}/join",
    response_model=JoinClubResponse,
    operation_id="joinClub",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def join_club(
    club_id: UUID,
    body: JoinClubRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> JoinClubResponse:
    _private(response)
    result = await _service(request, session).join(
        principal,
        club_id,
        message=body.message,
        request_id=UUID(request_id_for(request)),
    )
    return JoinClubResponse(
        state=result.state,
        membership_id=result.membership.id if result.membership else None,
        join_request_id=result.join_request.id if result.join_request else None,
    )


@router.delete(
    "/{club_id:uuid}/membership",
    response_model=OperationResponse,
    operation_id="leaveClub",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def leave_club(
    club_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> OperationResponse:
    _private(response)
    await _service(request, session).leave(
        principal,
        club_id,
        request_id=UUID(request_id_for(request)),
    )
    return OperationResponse(status="left")


@router.get(
    "/{club_id:uuid}/members",
    response_model=MemberPageResponse,
    operation_id="listClubMembers",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND},
)
async def list_club_members(
    club_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> MemberPageResponse:
    _private(response)
    return MemberPageResponse(
        items=[
            _member(item)
            for item in await _service(request, session).list_members(principal, club_id)
        ]
    )


@router.get(
    "/{club_id:uuid}/join-requests",
    response_model=JoinRequestPageResponse,
    operation_id="listClubJoinRequests",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND},
)
async def list_club_join_requests(
    club_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> JoinRequestPageResponse:
    _private(response)
    return JoinRequestPageResponse(
        items=[
            _join_request(item)
            for item in await _service(request, session).list_requests(principal, club_id)
        ]
    )


@router.post(
    "/{club_id:uuid}/join-requests/{join_request_id:uuid}/approve",
    response_model=OperationResponse,
    operation_id="approveClubJoinRequest",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def approve_club_join_request(
    club_id: UUID,
    join_request_id: UUID,
    body: DecisionRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> OperationResponse:
    _private(response)
    await _service(request, session).approve(
        principal,
        club_id,
        join_request_id,
        reason=body.reason,
        request_id=UUID(request_id_for(request)),
    )
    return OperationResponse(status="approved")


@router.post(
    "/{club_id:uuid}/join-requests/{join_request_id:uuid}/reject",
    response_model=OperationResponse,
    operation_id="rejectClubJoinRequest",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def reject_club_join_request(
    club_id: UUID,
    join_request_id: UUID,
    body: DecisionRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> OperationResponse:
    _private(response)
    await _service(request, session).reject(
        principal,
        club_id,
        join_request_id,
        reason=body.reason,
        request_id=UUID(request_id_for(request)),
    )
    return OperationResponse(status="rejected")


@router.patch(
    "/{club_id:uuid}/members/{user_id:uuid}/role",
    response_model=OperationResponse,
    operation_id="changeClubMemberRole",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def change_club_member_role(
    club_id: UUID,
    user_id: UUID,
    body: RoleChangeRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> OperationResponse:
    _private(response)
    await _service(request, session).change_role(
        principal,
        club_id,
        user_id,
        role=body.role,
        reason=body.reason,
        request_id=UUID(request_id_for(request)),
    )
    return OperationResponse(status="role_changed")


@router.post(
    "/{club_id:uuid}/ownership-transfer",
    response_model=OperationResponse,
    operation_id="transferClubOwnership",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def transfer_club_ownership(
    club_id: UUID,
    body: OwnershipTransferRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> OperationResponse:
    _private(response)
    await _service(request, session).transfer(
        principal,
        club_id,
        body.target_user_id,
        reason=body.reason,
        request_id=UUID(request_id_for(request)),
    )
    return OperationResponse(status="transferred")


@router.post(
    "/{club_id:uuid}/close",
    response_model=OperationResponse,
    operation_id="closeClub",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def close_club(
    club_id: UUID,
    body: CloseClubRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> OperationResponse:
    _private(response)
    await _service(request, session).close(
        principal,
        club_id,
        reason=body.reason,
        request_id=UUID(request_id_for(request)),
    )
    return OperationResponse(status="closed")


__all__ = ["router"]
