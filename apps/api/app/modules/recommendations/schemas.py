from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RecommendationEventCreate(BaseModel):
    event_id: str
    source: str = Field(default="hybrid", min_length=1, max_length=80)
    score: Decimal | None = Field(default=None, ge=0, le=1)
    action: str = Field(
        default="impression", pattern="^(impression|click|save|register)$"
    )


class RecommendationEventState(BaseModel):
    id: str
    user_id: str
    event_id: str
    source: str
    score: Decimal | None = None
    action: str
    created_at: datetime
