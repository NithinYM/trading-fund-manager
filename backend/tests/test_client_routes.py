from datetime import date

from fastapi.testclient import TestClient

from app.db.database import Base, SessionLocal, engine
from app.main import app
from app.models.client import Client
from app.models.client_ledger import ClientLedger
from app.models.client_status_history import ClientStatusHistory
from app.models.daily_trading import DailyTrading
from app.models.fund_movement import FundMovement

Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_client_routes_can_create_and_list_clients(auth_headers):
    payload = {
        "client_code": "C1001",
        "name": "API Client",
        "opening_capital": 20000,
        "join_date": "2026-02-01",
        "status": "ACTIVE",
        "fee_type": "NONE",
        "fee_value": 0,
    }

    create_response = client.post("/clients", json=payload, headers=auth_headers)
    assert create_response.status_code == 200, create_response.text
    created = create_response.json()
    assert created["client_code"] == "C1001"
    assert created["name"] == "API Client"

    list_response = client.get("/clients")
    assert list_response.status_code == 200, list_response.text
    items = list_response.json()
    assert any(item["client_code"] == "C1001" for item in items)


def test_client_detail_route_returns_summary_and_ledger(auth_headers):
    with SessionLocal() as db:
        db.add(
            Client(
                id="client-detail-1",
                client_code="CD01",
                name="Detail Client",
                opening_capital=10000,
                join_date=date(2026, 1, 1),
                status="ACTIVE",
                fee_type="NONE",
                fee_value=0,
            )
        )
        db.add(
            FundMovement(
                id="movement-1",
                date=date(2026, 1, 2),
                client_id="client-detail-1",
                movement_type="DEPOSIT",
                amount=1000,
                signed_amount=1000,
            )
        )
        db.add(
            ClientLedger(
                id="ledger-1",
                trading_date=date(2026, 1, 2),
                client_id="client-detail-1",
                fund_movement=1000,
                capital_before_pnl=10000,
                capital_share_percent=100,
                net_daily_pnl=500,
                allocated_pnl=500,
                fee_debited=0,
                net_client_pnl=500,
                closing_balance=11500,
                daily_return_percent=5,
                status_on_date="ACTIVE",
                manager_fee_credit=0,
                calculation_version="v1",
            )
        )
        db.commit()

    response = client.get("/clients/client-detail-1/detail", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["summary"]["current_capital"] == "11500.00"
    assert payload["summary"]["total_allocated_pnl"] == "500.00"
    assert len(payload["ledger"]) == 1


def test_trading_allocation_route_reconciles_daily_pnl(auth_headers):
    with SessionLocal() as db:
        db.add_all(
            [
                Client(
                    id="trade-client-1",
                    client_code="TA01",
                    name="Active One",
                    opening_capital=60000,
                    join_date=date(2026, 1, 1),
                    status="ACTIVE",
                    fee_type="PERCENTAGE",
                    fee_value=10,
                ),
                Client(
                    id="trade-client-2",
                    client_code="TA02",
                    name="Active Two",
                    opening_capital=40000,
                    join_date=date(2026, 1, 1),
                    status="ACTIVE",
                    fee_type="NONE",
                    fee_value=0,
                ),
                Client(
                    id="trade-client-3",
                    client_code="TA03",
                    name="Inactive One",
                    opening_capital=25000,
                    join_date=date(2026, 1, 1),
                    status="INACTIVE",
                    fee_type="NONE",
                    fee_value=0,
                ),
                ClientStatusHistory(
                    id="status-1",
                    client_id="trade-client-3",
                    status="INACTIVE",
                    from_date=date(2026, 1, 1),
                    to_date=date(2026, 12, 31),
                ),
            ]
        )
        db.commit()

    create_response = client.post(
        "/trading",
        json={
            "trading_date": "2026-01-05",
            "gross_trading_pnl": 5000,
            "transaction_charges": 0,
            "remarks": "Market day",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 200, create_response.text

    allocation_response = client.get("/trading/2026-01-05/allocation", headers=auth_headers)
    assert allocation_response.status_code == 200, allocation_response.text
    payload = allocation_response.json()
    assert payload["active_capital"] == "100000.00"
    assert payload["allocation_difference"] == "0.00"
    assert payload["manager_fee"] == "300.00"
    assert payload["entries"][0]["allocated_pnl"] in {"3000.00", "2000.00"}
