from fastapi import APIRouter

from app.api.v1 import health, meta
from app.modules.auth.router import router as auth_router
from app.modules.clubs.router import router as clubs_router
from app.modules.events.router import router as events_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(meta.router, prefix="/meta", tags=["meta"])
api_router.include_router(auth_router)
api_router.include_router(clubs_router)
api_router.include_router(events_router)
