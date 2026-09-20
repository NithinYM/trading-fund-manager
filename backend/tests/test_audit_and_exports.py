from datetime import date

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.models.client import Client
from app.models.client_ledger import ClientLedger
from app.models.daily_trading import DailyTrading

client = TestClient(app)


def test_client_changes_are_available_in_audit_trail(auth_headers):
    response = client.post(
        "/clients",
        json={
            "client_code": "AUD001",
            "name": "Audited Client",
            "opening_capital": 10000,
            "join_date": "2026-01-01",
            "status": "ACTIVE",
            "fee_type": "NONE",
            "fee_value": 0,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    client_id = response.json()["id"]

    audit_response = client.get(f"/audit-logs?entity_type=CLIENT&entity_id={client_id}", headers=auth_headers)
    assert audit_response.status_code == 200, audit_response.text
    entries = audit_response.json()
    assert len(entries) == 1
    assert entries[0]["action"] == "CREATE"
    assert entries[0]["new_values"]["client_code"] == "AUD001"


def test_daily_report_csv_export_contains_summary_and_ledger_rows():
    with SessionLocal() as db:
        db.add(Client(id="export-client", client_code="EXP001", name="Export Client", opening_capital=10000, join_date=date(2026, 1, 1), status="ACTIVE", fee_type="NONE", fee_value=0))
        db.add(DailyTrading(id="export-trading", trading_date=date(2026, 1, 2), gross_trading_pnl=500, transaction_charges=50, net_pnl=450))
        db.add(ClientLedger(id="export-ledger", trading_date=date(2026, 1, 2), client_id="export-client", capital_before_pnl=10000, capital_share_percent=100, net_daily_pnl=450, allocated_pnl=450, fee_debited=0, net_client_pnl=450, closing_balance=10450, status_on_date="ACTIVE", manager_fee_credit=0))
        db.commit()

    response = client.get("/reports/daily/export?trading_date=2026-01-02")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert "daily-report-2026-01-02.csv" in response.headers["content-disposition"]
    assert "client_id,capital_before_pnl" in response.text
    assert "export-client" in response.text