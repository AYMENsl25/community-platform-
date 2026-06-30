from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.errors import configure_error_handlers


def test_http_errors_use_standard_error_shape() -> None:
    app = FastAPI()
    configure_error_handlers(app)

    @app.get("/missing")
    async def missing() -> None:
        raise HTTPException(status_code=404, detail="Thing not found")

    response = TestClient(app).get("/missing", headers={"X-Request-ID": "req_test"})

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Thing not found",
            "request_id": "req_test",
        }
    }


def test_validation_errors_use_standard_error_shape() -> None:
    app = FastAPI()
    configure_error_handlers(app)

    @app.get("/items/{item_id}")
    async def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    response = TestClient(app).get("/items/not-an-int")

    body = response.json()
    assert response.status_code == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Request validation failed."
    assert body["error"]["request_id"] == "unknown"
    assert body["error"]["details"][0]["loc"] == ["path", "item_id"]
