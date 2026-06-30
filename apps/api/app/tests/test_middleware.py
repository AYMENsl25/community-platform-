from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import middleware
from app.core.middleware import InMemoryRateLimiter, configure_security_middleware


def test_request_id_header_is_returned() -> None:
    app = FastAPI()
    configure_security_middleware(app)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).get("/ping", headers={"X-Request-ID": "req_visible"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req_visible"


def test_rate_limit_returns_standard_error(monkeypatch) -> None:
    app = FastAPI()
    monkeypatch.setattr(middleware, "rate_limiter", InMemoryRateLimiter(limit=1))
    configure_security_middleware(app)

    @app.get("/limited")
    async def limited() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/limited").status_code == 200

    response = client.get("/limited", headers={"X-Request-ID": "req_limited"})

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert response.json() == {
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Try again shortly.",
            "request_id": "req_limited",
        }
    }
