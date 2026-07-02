from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import request_metrics
from app.core.observability import observability_context
from app.db.session import get_db_session

router = APIRouter()


@router.get("/health/db")
async def database_health(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/metrics")
async def metrics() -> dict[str, object]:
    return {
        "requests": request_metrics.snapshot(),
        "observability": observability_context(),
    }
