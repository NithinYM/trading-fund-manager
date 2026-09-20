from datetime import date

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.models.client import Client
from app.models.client_ledger import ClientLedger
from app.models.client_status_history import ClientStatusHistory
from app.models.daily_trading import DailyTrading
from app.models.fund_movement import FundMovement

client = TestClient(app)


def test_dashboard_returns_current_aggregates():
    with SessionLocal() as db:
        db.add(
            Client(
                id="dashboard-client",
                client_code="C4001",
                name="Dashboard Client",
                opening_capital=10000,
                join_date=date(2026, 1, 1),
                status="ACTIVE",
                fee_type="NONE",
                fee_value=0,
            )
        )
        db.add(
            FundMovement(
                id="dashboard-movement",
                date=date.today(),
                client_id="dashboard-client",
                movement_type="DEPOSIT",
                amount=500,
                signed_amount=500,
            )
        )
        db.add(
            DailyTrading(
                id="dashboard-trading",
                trading_date=date.today(),
                gross_trading_pnl=1000,
                transaction_charges=100,
                net_pnl=900,
            )
        )
        db.commit()

    response = client.get("/dashboard")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_current_capital"] == "10500.00"
    assert data["current_month_pnl"] == "900.00"
    assert data["active_clients"] == 1
    assert data["today_pnl"] == "900.00"


def test_dashboard_active_clients_respect_today_status_history():
    with SessionLocal() as db:
        db.add(Client(id="historical-client", client_code="C4002", name="Historical", opening_capital=1000, join_date=date(2026, 1, 1), status="ACTIVE", fee_type="NONE", fee_value=0))
        today = date.today()
        db.add(ClientStatusHistory(id="historical-status", client_id="historical-client", status="INACTIVE", from_date=today, to_date=today))
        db.commit()

    response = client.get("/dashboard")
    assert response.status_code == 200, response.text
    assert response.json()["active_clients"] == 0


def test_dashboard_uses_latest_ledger_balance_for_current_capital():
    with SessionLocal() as db:
        db.add(Client(id="ledger-client", client_code="C4003", name="Ledger", opening_capital=10000, join_date=date(2026, 1, 1), status="ACTIVE", fee_type="NONE", fee_value=0))
        db.add(ClientLedger(id="ledger-row", trading_date=date(2026, 1, 2), client_id="ledger-client", capital_before_pnl=10000, capital_share_percent=100, net_daily_pnl=500, allocated_pnl=500, fee_debited=0, net_client_pnl=500, closing_balance=10500, status_on_date="ACTIVE", manager_fee_credit=0))
        db.commit()

    response = client.get("/dashboard")
    assert response.status_code == 200, response.text
    assert response.json()["total_current_capital"] == "10500.00"
