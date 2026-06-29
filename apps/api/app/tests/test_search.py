from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.search import service
from app.modules.search.schemas import SearchResult


class FakeSession:
    pass


@pytest.mark.asyncio
async def test_search_public_content_strips_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = [
        SearchResult(
            entity_type="club",
            entity_id="11111111-1111-1111-1111-111111111111",
            title="COMMUNITI AI Lab",
            body="AI builders community.",
            city="Riyadh",
            country="Saudi Arabia",
            created_at=datetime.now(UTC),
            rank=0.8,
        )
    ]
    seen_queries: list[str] = []

    async def fake_search_public_index(
        *args: object, q: str, **kwargs: object
    ) -> list[SearchResult]:
        seen_queries.append(q)
        return expected

    monkeypatch.setattr(service, "search_public_index", fake_search_public_index)

    result = await service.search_public_content(
        FakeSession(),  # type: ignore[arg-type]
        q="  AI Lab  ",
        limit=20,
        offset=0,
    )

    assert result == expected
    assert seen_queries == ["AI Lab"]


def test_openapi_includes_search_route() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/search" in response.json()["paths"]
