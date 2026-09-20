from datetime import datetime, timezone
from hashlib import sha256

import bcrypt
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.db.database import SessionLocal
from app.main import app
from app.models.user import User

client = TestClient(app)


def password_hash(password: str) -> str:
    return bcrypt.hashpw(sha256(password.encode("utf-8")).digest(), bcrypt.gensalt()).decode("utf-8")


def test_login_returns_signed_access_token_for_valid_user():
    with SessionLocal() as db:
        db.add(User(id="auth-user", username="manager", email="manager@example.com", password_hash=password_hash("correct"), role="ADMIN", is_active=True))
        db.commit()

    response = client.post("/auth/login", json={"username": "manager", "password": "correct"})
    assert response.status_code == 200, response.text
    payload = response.json()
    claims = jwt.decode(payload["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert claims["sub"] == "auth-user"
    assert claims["role"] == "ADMIN"
    assert datetime.fromtimestamp(claims["exp"], timezone.utc) > datetime.now(timezone.utc)


def test_login_rejects_invalid_password():
    with SessionLocal() as db:
        db.add(User(id="auth-user-2", username="manager2", email="manager2@example.com", password_hash=password_hash("correct"), role="ADMIN", is_active=True))
        db.commit()

    response = client.post("/auth/login", json={"username": "manager2", "password": "wrong"})
    assert response.status_code == 401


def test_login_rejects_malformed_stored_password_hash():
    with SessionLocal() as db:
        db.add(User(id="auth-user-malformed", username="broken", email="broken@example.com", password_hash="not-a-bcrypt-hash", role="ADMIN", is_active=True))
        db.commit()

    response = client.post("/auth/login", json={"username": "broken", "password": "correct"})
    assert response.status_code == 401


def test_me_requires_and_resolves_bearer_token():
    with SessionLocal() as db:
        db.add(User(id="auth-user-3", username="manager3", email="manager3@example.com", password_hash=password_hash("correct"), role="TRADER", is_active=True))
        db.commit()

    login_response = client.post("/auth/login", json={"username": "manager3", "password": "correct"})
    token = login_response.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    assert response.json() == {"id": "auth-user-3", "username": "manager3", "role": "TRADER"}

    forbidden = client.post("/reports/recalculate/2026-01-01", headers={"Authorization": f"Bearer {token}"})
    assert forbidden.status_code == 403

    trading_forbidden = client.post(
        "/trading",
        json={"trading_date": "2026-01-01", "gross_trading_pnl": 100, "transaction_charges": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert trading_forbidden.status_code == 403

    client_forbidden = client.post(
        "/clients",
        json={"client_code": "VIEW001", "name": "Viewer Attempt", "opening_capital": 1000, "join_date": "2026-01-01", "fee_type": "NONE", "fee_value": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert client_forbidden.status_code == 403

    missing_token = client.get("/auth/me")
    assert missing_token.status_code == 401
