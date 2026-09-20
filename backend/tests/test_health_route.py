from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_readiness_checks_database():
    response = client.get("/health/ready")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ready", "database": "ok"}
