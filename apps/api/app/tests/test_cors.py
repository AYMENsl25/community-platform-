from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.cors import configure_cors


def test_development_cors_allows_localhost_ports_for_dev_auth_header() -> None:
    app = FastAPI()
    configure_cors(app)
    client = TestClient(app)

    response = client.options(
        "/api/v1/events/example/register",
        headers={
            "Origin": "http://127.0.0.1:3025",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-communiti-user-email",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3025"
