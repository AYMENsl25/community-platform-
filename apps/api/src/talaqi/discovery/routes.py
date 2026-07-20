from __future__ import annotations

from datetime import date
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.config import Settings
from talaqi.discovery.models import (
    ClubPosition,
    DiscoveryFilters,
    DiscoveryPosition,
    PriceType,
    SearchPosition,
)
from talaqi.discovery.repository import DiscoveryRepository
from talaqi.discovery.schemas import (
    ClubCardResponse,
    ClubDetailResponse,
    ClubPageResponse,
    DiscoveryMetadataResponse,
    EventCardResponse,
    EventPageResponse,
    SearchItemResponse,
    SearchPageResponse,
)
from talaqi.discovery.service import DiscoveryCursorCodec
from talaqi.identity.dependencies import (
    CsrfProtection,
    CurrentPrincipal,
    DatabaseSession,
    build_auth_service,
)
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.platform.errors import ErrorEnvelope
from talaqi.profiles.eligibility import CreationEligibilityService
from talaqi.profiles.repository import ProfileRepository
from talaqi.regions.repository import RegionRepository
from talaqi.regions.service import RegionPolicyService

router = APIRouter(prefix="/api/v1", tags=["discovery"])
_NOT_FOUND: dict[str, Any] = {"model": ErrorEnvelope, "description": "Public resource not found."}
_AUTH: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication required."}
_FORBIDDEN: dict[str, Any] = {"model": ErrorEnvelope, "description": "Capability or CSRF denied."}


async def _optional_principal(request: Request, session: DatabaseSession) -> AuthPrincipal | None:
    if request.cookies.get("talaqi_access") is None:
        return None
    try:
        return await build_auth_service(request, session).require_user(request)
    except ApiError as error:
        if error.status_code == 401:
            return None
        raise


OptionalPrincipal = Annotated[AuthPrincipal | None, Depends(_optional_principal)]


def _caller_aware_response(response: Response, principal: AuthPrincipal | None) -> None:
    response.headers["Vary"] = "Cookie"
    response.headers["Cache-Control"] = (
        "private, no-store" if principal is not None else "public, max-age=60, s-maxage=300"
    )


def _public_response(response: Response) -> None:
    response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300"


def _filters(
    country: str | None,
    city: str | None,
    category: str | None,
    date_from: date | None,
    date_to: date | None,
    price: str | None,
    search: str | None,
) -> DiscoveryFilters:
    try:
        return DiscoveryFilters(
            country=country,
            city=city,
            category=category,
            date_from=date_from,
            date_to=date_to,
            price=cast(PriceType | None, price),
            search=search,
        )
    except ValueError:
        raise ApiError(
            code="invalid_filters", message_key="errors.validation", status_code=422
        ) from None


def _codec(request: Request) -> DiscoveryCursorCodec:
    settings: Settings = request.app.state.settings_factory()
    return DiscoveryCursorCodec(settings.session_secret.get_secret_value().encode())


async def _require_save_capability(
    request: Request, session: AsyncSession, principal: AuthPrincipal
) -> None:
    settings: Settings = request.app.state.settings_factory()
    repository = ProfileRepository(session)
    eligibility = CreationEligibilityService(
        repository,
        RegionPolicyService(RegionRepository(session)),
        current_terms_version=settings.current_terms_version,
        current_privacy_version=settings.current_privacy_version,
        current_organizer_rules_version=settings.current_organizer_rules_version,
        current_community_rules_version=settings.current_community_rules_version,
        admin_mfa_required=settings.admin_mfa_required,
    )
    capabilities = await eligibility.evaluate(principal)
    if not capabilities.save_event:
        blocker = capabilities.blockers[0] if capabilities.blockers else "forbidden"
        raise ApiError(code=blocker, message_key=f"blockers.{blocker}", status_code=403)


async def _event_page(
    request: Request,
    session: AsyncSession,
    filters: DiscoveryFilters,
    *,
    limit: int,
    cursor: str | None,
    caller_id: UUID | None = None,
    saved_only: bool = False,
) -> EventPageResponse:
    codec = _codec(request)
    after = codec.decode(cursor, filters) if cursor else None
    events = await DiscoveryRepository(session).list_events(
        filters, limit=limit + 1, after=after, caller_id=caller_id, saved_only=saved_only
    )
    page = events[:limit]
    next_cursor = None
    if len(events) > limit and page:
        last = page[-1]
        next_cursor = codec.encode(
            filters, DiscoveryPosition(last.featured_score, last.start_at, last.id)
        )
    return EventPageResponse(
        items=[EventCardResponse.model_validate(item) for item in page],
        next_cursor=next_cursor,
    )


@router.get("/events", response_model=EventPageResponse, operation_id="listEvents")
async def list_events(
    request: Request,
    response: Response,
    session: DatabaseSession,
    principal: OptionalPrincipal,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    city: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    price: Annotated[str | None, Query(pattern="^(free|cash)$")] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> EventPageResponse:
    _caller_aware_response(response, principal)
    filters = _filters(country, city, category, date_from, date_to, price, search)
    return await _event_page(
        request,
        session,
        filters,
        limit=limit,
        cursor=cursor,
        caller_id=principal.user_id if principal else None,
    )


@router.get(
    "/events/{event_id}",
    response_model=EventCardResponse,
    operation_id="getEvent",
    responses={404: _NOT_FOUND},
)
async def get_event(
    event_id: UUID,
    response: Response,
    session: DatabaseSession,
    principal: OptionalPrincipal,
) -> EventCardResponse:
    _caller_aware_response(response, principal)
    event = await DiscoveryRepository(session).get_event(
        event_id, caller_id=principal.user_id if principal else None
    )
    if event is None:
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
    return EventCardResponse.model_validate(event)


@router.get("/clubs", response_model=ClubPageResponse, operation_id="listClubs")
async def list_clubs(
    request: Request,
    response: Response,
    session: DatabaseSession,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    city: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> ClubPageResponse:
    _public_response(response)
    filters = _filters(country, city, category, None, None, None, search)
    codec = _codec(request)
    after = codec.decode_club(cursor, filters) if cursor else None
    clubs = await DiscoveryRepository(session).list_clubs(filters, limit=limit + 1, after=after)
    page = clubs[:limit]
    next_cursor = None
    if len(clubs) > limit and page:
        last = page[-1]
        next_cursor = codec.encode_club(filters, ClubPosition(name_key=last.name_key, id=last.id))
    return ClubPageResponse(
        items=[ClubCardResponse.model_validate(club) for club in page],
        next_cursor=next_cursor,
    )


@router.get(
    "/clubs/{slug}",
    response_model=ClubDetailResponse,
    operation_id="getClub",
    responses={404: _NOT_FOUND},
)
async def get_club(
    slug: str,
    response: Response,
    session: DatabaseSession,
    principal: OptionalPrincipal,
) -> ClubDetailResponse:
    _caller_aware_response(response, principal)
    repository = DiscoveryRepository(session)
    normalized_slug = slug.casefold()
    club = await repository.get_club(normalized_slug)
    if club is None:
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
    events = await repository.list_events(
        DiscoveryFilters(),
        limit=50,
        club_slug=normalized_slug,
        caller_id=principal.user_id if principal else None,
    )
    return ClubDetailResponse(
        **ClubCardResponse.model_validate(club).model_dump(),
        events=[EventCardResponse.model_validate(event) for event in events],
    )


@router.get("/search", response_model=SearchPageResponse, operation_id="searchDiscovery")
async def search_discovery(
    request: Request,
    response: Response,
    session: DatabaseSession,
    search: Annotated[str, Query(min_length=1, max_length=120)],
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    city: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> SearchPageResponse:
    _public_response(response)
    filters = _filters(country, city, category, None, None, None, search)
    codec = _codec(request)
    after = codec.decode_search(cursor, filters) if cursor else None
    results = await DiscoveryRepository(session).search(filters, limit=limit + 1, after=after)
    page = results[:limit]
    next_cursor = None
    if len(results) > limit and page:
        last = page[-1]
        next_cursor = codec.encode_search(
            filters,
            SearchPosition(title_key=last.title_key, kind=last.kind, id=last.id),
        )
    return SearchPageResponse(
        items=[SearchItemResponse.model_validate(item) for item in page],
        next_cursor=next_cursor,
    )


@router.get(
    "/metadata", response_model=DiscoveryMetadataResponse, operation_id="getDiscoveryMetadata"
)
async def get_metadata(response: Response, session: DatabaseSession) -> DiscoveryMetadataResponse:
    _public_response(response)
    service = RegionPolicyService(RegionRepository(session))
    countries = await service.list_countries()
    cities = await service.list_cities(None)
    categories = await service.list_categories()
    return DiscoveryMetadataResponse(
        countries=[{"code": value.code, "name_key": value.name_key} for value in countries],
        cities=[{"slug": value.slug, "name_key": value.name_key} for value in cities],
        categories=[{"slug": value.slug, "name_key": value.name_key} for value in categories],
    )


@router.put(
    "/events/{event_id}/saved",
    status_code=204,
    operation_id="saveEvent",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND},
)
async def save_event(
    event_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> Response:
    await _require_save_capability(request, session, principal)
    if not await DiscoveryRepository(session).save_event(principal.user_id, event_id):
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/events/{event_id}/saved",
    status_code=204,
    operation_id="unsaveEvent",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND},
)
async def unsave_event(
    event_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> Response:
    await _require_save_capability(request, session, principal)
    if not await DiscoveryRepository(session).unsave_event(principal.user_id, event_id):
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me/saved-events",
    response_model=EventPageResponse,
    operation_id="listSavedEvents",
    responses={401: _AUTH},
)
async def list_saved_events(
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> EventPageResponse:
    _caller_aware_response(response, principal)
    return await _event_page(
        request,
        session,
        DiscoveryFilters(),
        limit=limit,
        cursor=cursor,
        caller_id=principal.user_id,
        saved_only=True,
    )


__all__ = ["router"]
