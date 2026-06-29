from datetime import datetime

from pydantic import BaseModel


class SearchResult(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    body: str | None = None
    city: str | None = None
    country: str | None = None
    created_at: datetime
    rank: float
