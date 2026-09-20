from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_fund_movement_sets_signed_amount_from_type(auth_headers):
    client_response = client.post(
        "/clients",
        json={
            "client_code": "C3001",
            "name": "Movement Client",
            "opening_capital": 10000,
            "join_date": "2026-01-01",
            "status": "ACTIVE",
            "fee_type": "NONE",
            "fee_value": 0,
        },
        headers=auth_headers,
    )
    client_id = client_response.json()["id"]

    response = client.post(
        "/fund-movements",
        json={
            "date": "2026-09-19",
            "client_id": client_id,
            "movement_type": "WITHDRAWAL",
            "amount": 1250,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["signed_amount"] == "-1250.00"
