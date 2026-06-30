from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def configure_cors(app: FastAPI) -> None:
    local_dev_origin_regex = (
        r"^https?://(localhost|127\.0\.0\.1):\d+$"
        if settings.environment == "development"
        else None
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,
        allow_origin_regex=local_dev_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Communiti-User-Email",
        ],
    )
