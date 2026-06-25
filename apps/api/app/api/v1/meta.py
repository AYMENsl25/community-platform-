from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

router = APIRouter()


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None


class TagResponse(BaseModel):
    id: str
    name: str
    slug: str


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(session: AsyncSession = Depends(get_db_session)) -> list[CategoryResponse]:
    result = await session.execute(
        text(
            """
            SELECT id::text AS id, name, slug, description
            FROM club_categories
            ORDER BY name
            """
        )
    )
    return [CategoryResponse.model_validate(row._mapping) for row in result]


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(session: AsyncSession = Depends(get_db_session)) -> list[TagResponse]:
    result = await session.execute(
        text(
            """
            SELECT id::text AS id, name, slug
            FROM club_tags
            ORDER BY name
            """
        )
    )
    return [TagResponse.model_validate(row._mapping) for row in result]
