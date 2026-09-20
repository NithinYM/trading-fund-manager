from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_recalculate_report_returns_persisted_ledger_rows(auth_headers):
    client_response = client.post(
        "/clients",
        json={
            "client_code": "R001",
            "name": "Report Client",
            "opening_capital": 10000,
            "join_date": "2026-01-01",
            "status": "ACTIVE",
            "fee_type": "NONE",
            "fee_value": 0,
        },
        headers=auth_headers,
    )
    assert client_response.status_code == 200, client_response.text

    trading_response = client.post(
        "/trading",
        json={
            "trading_date": "2026-01-02",
            "gross_trading_pnl": 1000,
            "transaction_charges": 100,
            "net_pnl": 0,
        },
        headers=auth_headers,
    )
    assert trading_response.status_code == 200, trading_response.text

    response = client.post("/reports/recalculate/2026-01-02", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["entries"][0]["allocated_pnl"] == "900.00"
    assert response.json()["entries"][0]["closing_balance"] == "10900.00"
