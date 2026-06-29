from fastapi import APIRouter

from app.api.v1 import health, meta
from app.modules.auth.router import router as auth_router
from app.modules.clubs.router import router as clubs_router
from app.modules.events.router import router as events_router
from app.modules.me.router import router as me_router
from app.modules.recommendations.router import router as recommendations_router
from app.modules.search.router import router as search_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(meta.router, prefix="/meta", tags=["meta"])
api_router.include_router(auth_router)
api_router.include_router(me_router)
api_router.include_router(clubs_router)
api_router.include_router(events_router)
api_router.include_router(search_router)
api_router.include_router(recommendations_router)
