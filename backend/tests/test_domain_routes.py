from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_client(client_code: str, auth_headers: dict[str, str]) -> str:
    response = client.post(
        "/clients",
        json={
            "client_code": client_code,
            "name": "Domain Client",
            "opening_capital": 10000,
            "join_date": "2026-01-01",
            "status": "ACTIVE",
            "fee_type": "NONE",
            "fee_value": 0,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_status_history_rejects_overlapping_periods(auth_headers):
    client_id = create_client("C2001", auth_headers)
    first = client.post(
        "/status-history",
        json={
            "client_id": client_id,
            "status": "ACTIVE",
            "from_date": "2026-01-01",
            "to_date": "2026-06-30",
        },
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text

    overlapping = client.post(
        "/status-history",
        json={
            "client_id": client_id,
            "status": "INACTIVE",
            "from_date": "2026-06-30",
            "to_date": "2026-12-31",
        },
        headers=auth_headers,
    )
    assert overlapping.status_code == 400
    assert "overlap" in overlapping.json()["detail"][0].lower()


def test_trading_route_calculates_net_pnl(auth_headers):
    response = client.post(
        "/trading",
        json={
            "trading_date": "2026-09-19",
            "gross_trading_pnl": 5000,
            "transaction_charges": 250,
            "net_pnl": 999999,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["net_pnl"] == "4750.00"


def test_admin_can_delete_only_the_latest_trading_result(auth_headers):
    for trading_date in ("2026-09-18", "2026-09-19"):
        response = client.post(
            "/trading",
            json={"trading_date": trading_date, "gross_trading_pnl": 5000, "transaction_charges": 250},
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text

    locked = client.delete("/trading/2026-09-18", headers=auth_headers)
    assert locked.status_code == 409

    deleted = client.delete("/trading/2026-09-19", headers=auth_headers)
    assert deleted.status_code == 200, deleted.text
