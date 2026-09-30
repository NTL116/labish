from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_metadata_middleware_adds_headers() -> None:
    response = client.get("/health")

    assert response.headers["x-request-id"]
    assert float(response.headers["x-response-time-ms"]) >= 0