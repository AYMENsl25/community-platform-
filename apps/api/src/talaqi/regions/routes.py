from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.platform.errors import ErrorEnvelope
from talaqi.regions.repository import RegionRepository
from talaqi.regions.schemas import (
    CategoryResponse,
    CityResponse,
    CountryResponse,
    RegionPolicyResponse,
)
from talaqi.regions.service import RegionPolicyService
from talaqi.runtime import get_db_session

router = APIRouter(prefix="/api/v1", tags=["regions"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session, scope="function")]


def _service(session: AsyncSession) -> RegionPolicyService:
    return RegionPolicyService(RegionRepository(session))


@router.get(
    "/countries",
    response_model=list[CountryResponse],
    operation_id="listCountries",
)
async def list_countries(session: DatabaseSession) -> list[CountryResponse]:
    countries = await _service(session).list_countries()
    return [CountryResponse.model_validate(country) for country in countries]


@router.get(
    "/cities",
    response_model=list[CityResponse],
    operation_id="listCities",
)
async def list_cities(
    session: DatabaseSession,
    country_code: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
) -> list[CityResponse]:
    cities = await _service(session).list_cities(country_code)
    return [CityResponse.model_validate(city) for city in cities]


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    operation_id="listCategories",
)
async def list_categories(session: DatabaseSession) -> list[CategoryResponse]:
    categories = await _service(session).list_categories()
    return [CategoryResponse.model_validate(category) for category in categories]


@router.get(
    "/regions/{country_code}/policy",
    response_model=RegionPolicyResponse,
    operation_id="getRegionPolicy",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorEnvelope,
            "description": "The requested enabled region does not exist.",
        }
    },
)
async def get_region_policy(country_code: str, session: DatabaseSession) -> RegionPolicyResponse:
    policy = await _service(session).get(country_code)
    return RegionPolicyResponse.model_validate(policy)
