from datetime import date

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.models.client import Client
from app.models.client_ledger import ClientLedger
from app.models.client_status_history import ClientStatusHistory
from app.models.daily_trading import DailyTrading
from app.models.manager_account import ManagerAccount

client = TestClient(app)


def test_daily_report_returns_trading_and_ledger_totals():
    with SessionLocal() as db:
        db.add(Client(id="summary-client", client_code="S001", name="Summary", opening_capital=10000, join_date=date(2026, 1, 1), status="ACTIVE", fee_type="NONE", fee_value=0))
        db.add(DailyTrading(id="summary-trading", trading_date=date(2026, 1, 2), gross_trading_pnl=1000, transaction_charges=100, net_pnl=900))
        db.add(ClientLedger(id="summary-ledger", trading_date=date(2026, 1, 2), client_id="summary-client", capital_before_pnl=10000, capital_share_percent=100, net_daily_pnl=900, allocated_pnl=900, fee_debited=0, net_client_pnl=900, closing_balance=10900, status_on_date="ACTIVE", manager_fee_credit=0))
        db.commit()

    response = client.get("/reports/daily?trading_date=2026-01-02")
    assert response.status_code == 200, response.text
    assert response.json()["net_pnl"] == "900.00"
    assert response.json()["allocated_pnl"] == "900.00"
    assert response.json()["ledger_entries"] == 1


def test_monthly_report_aggregates_trading_rows():
    with SessionLocal() as db:
        db.add(DailyTrading(id="month-trading-1", trading_date=date(2026, 2, 1), gross_trading_pnl=500, transaction_charges=50, net_pnl=450))
        db.add(DailyTrading(id="month-trading-2", trading_date=date(2026, 2, 2), gross_trading_pnl=600, transaction_charges=60, net_pnl=540))
        db.commit()

    response = client.get("/reports/monthly?year=2026&month=2")
    assert response.status_code == 200, response.text
    assert response.json()["net_pnl"] == "990.00"
    assert response.json()["trading_days"] == 2


def test_reconciliation_report_exposes_control_deltas():
    with SessionLocal() as db:
        db.add(Client(id="recon-client", client_code="S002", name="Recon", opening_capital=10000, join_date=date(2026, 1, 1), status="ACTIVE", fee_type="NONE", fee_value=0))
        db.add(DailyTrading(id="recon-trading", trading_date=date(2026, 3, 1), gross_trading_pnl=1000, transaction_charges=100, net_pnl=900))
        db.add(ClientLedger(id="recon-ledger", trading_date=date(2026, 3, 1), client_id="recon-client", capital_before_pnl=10000, capital_share_percent=100, net_daily_pnl=900, allocated_pnl=900, fee_debited=25, net_client_pnl=875, closing_balance=10875, status_on_date="ACTIVE", manager_fee_credit=25))
        db.commit()

    response = client.get("/reports/reconciliation/2026-03-01")
    assert response.status_code == 200, response.text
    assert response.json()["allocation_reconciled"] is True
    assert response.json()["fees_reconciled"] is True
    assert response.json()["fee_transfer_delta"] == "0.00"


def test_client_detail_includes_richer_reconciliation_summary_and_status_history(auth_headers):
    with SessionLocal() as db:
        db.add(Client(id="rich-client", client_code="R001", name="Rich Client", opening_capital=10000, join_date=date(2026, 1, 1), status="ACTIVE", fee_type="PERCENTAGE", fee_value=2.5))
        db.add(ClientStatusHistory(id="rich-hist-1", client_id="rich-client", status="ACTIVE", from_date=date(2026, 1, 1), to_date=date(2026, 6, 30)))
        db.add(ClientStatusHistory(id="rich-hist-2", client_id="rich-client", status="INACTIVE", from_date=date(2026, 7, 1), to_date=date(2026, 12, 31)))
        db.add(ClientLedger(id="rich-ledger-1", trading_date=date(2026, 1, 5), client_id="rich-client", capital_before_pnl=10000, capital_share_percent=100, net_daily_pnl=900, allocated_pnl=900, fee_debited=22.5, net_client_pnl=877.5, closing_balance=10877.5, status_on_date="ACTIVE", manager_fee_credit=22.5))
        db.commit()

    response = client.get("/clients/rich-client/detail", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["summary"]["manager_fee_credit_total"] == "22.50"
    assert payload["summary"]["fee_transfer_delta"] == "0.00"
    assert payload["summary"]["current_status"] == "INACTIVE"
    assert payload["status_history"][0]["status"] == "ACTIVE"
    assert payload["status_history"][-1]["status"] == "INACTIVE"


def test_manager_account_reconciliation_summary_tracks_balance_and_fee_credits():
    with SessionLocal() as db:
        db.add(ManagerAccount(id="acct-1", code="MGR-01", name="Treasury", opening_capital=5000))
        db.add(Client(id="mgr-client", client_code="M001", name="Manager Client", opening_capital=20000, join_date=date(2026, 1, 1), status="ACTIVE", fee_type="PERCENTAGE", fee_value=5))
        db.add(DailyTrading(id="mgr-trading", trading_date=date(2026, 4, 1), gross_trading_pnl=1000, transaction_charges=100, net_pnl=900))
        db.add(ClientLedger(id="mgr-ledger", trading_date=date(2026, 4, 1), client_id="mgr-client", capital_before_pnl=20000, capital_share_percent=100, net_daily_pnl=900, allocated_pnl=900, fee_debited=45, net_client_pnl=855, closing_balance=20855, status_on_date="ACTIVE", manager_fee_credit=45))
        db.commit()

    response = client.get("/manager-accounts/MGR-01/reconciliation?trading_date=2026-04-01")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["opening_capital"] == "5000.00"
    assert payload["fees_received"] == "45.00"
    assert payload["current_balance"] == "5045.00"
    assert payload["fees_reconciled"] is True


def test_manager_account_list_returns_accounts_with_reconciliation_status():
    with SessionLocal() as db:
        db.add(ManagerAccount(id="acct-1", code="MGR-01", name="Treasury", opening_capital=5000))
        db.add(ManagerAccount(id="acct-2", code="MGR-02", name="Side Pocket", opening_capital=2500))
        db.commit()

    response = client.get("/manager-accounts")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["code"] in {"MGR-01", "MGR-02"}
