import os
from hashlib import sha256
from pathlib import Path

import bcrypt
import pytest
from fastapi.testclient import TestClient

TEST_DATABASE_PATH = Path(__file__).resolve().parent / "test_app.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

from app.db.database import Base, SessionLocal, engine
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def auth_headers():
    password_hash = bcrypt.hashpw(sha256(b"test-password").digest(), bcrypt.gensalt()).decode("utf-8")
    with SessionLocal() as db:
        db.add(User(id="test-admin", username="test-admin", email="test-admin@example.com", password_hash=password_hash, role="ADMIN", is_active=True))
        db.commit()

    response = TestClient(app).post("/auth/login", json={"username": "test-admin", "password": "test-password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)
