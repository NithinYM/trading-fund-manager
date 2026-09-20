from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.client import Client
from app.models.client_ledger import ClientLedger
from app.models.client_status_history import ClientStatusHistory
from app.models.daily_trading import DailyTrading
from app.models.fund_movement import FundMovement

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _money(value: Decimal | None) -> str:
    return f"{value or Decimal('0.00'):.2f}"


@router.get("")
def dashboard(db: Session = Depends(get_db)) -> dict[str, object]:
    today = date.today()
    month_start = today.replace(day=1)
    clients = db.query(Client).filter(Client.is_deleted.is_(False)).all()
    movements = db.query(FundMovement).all()
    trading = db.query(DailyTrading).all()
    ledger = db.query(ClientLedger).all()
    histories = (
        db.query(ClientStatusHistory)
        .filter(ClientStatusHistory.from_date <= today, ClientStatusHistory.to_date >= today)
        .order_by(ClientStatusHistory.from_date.desc())
        .all()
    )
    status_by_client = {}
    for history in histories:
        status_by_client.setdefault(history.client_id, history.status)

    current_capital = Decimal("0.00")
    for client in clients:
        latest_ledger = (
            db.query(ClientLedger)
            .filter(ClientLedger.client_id == client.id)
            .order_by(ClientLedger.trading_date.desc())
            .first()
        )
        if latest_ledger:
            current_capital += Decimal(str(latest_ledger.closing_balance or "0.00"))
            continue
        movement_total = sum((movement.signed_amount or Decimal("0.00") for movement in client.fund_movements), Decimal("0.00"))
        current_capital += Decimal(str(client.opening_capital or "0.00")) + movement_total
    current_month_trading = sum(
        (record.net_pnl or Decimal("0.00") for record in trading if month_start <= record.trading_date <= today),
        Decimal("0.00"),
    )
    total_net_pnl = sum((record.net_pnl or Decimal("0.00") for record in trading), Decimal("0.00"))
    total_fees = sum((entry.fee_debited or Decimal("0.00") for entry in ledger), Decimal("0.00"))
    today_pnl = sum((record.net_pnl or Decimal("0.00") for record in trading if record.trading_date == today), Decimal("0.00"))

    active_clients = 0
    for client in clients:
        status = status_by_client.get(client.id, client.status)
        if status == "ACTIVE":
            active_clients += 1

    return {
        "total_current_capital": _money(current_capital),
        "current_month_pnl": _money(current_month_trading),
        "total_net_pnl": _money(total_net_pnl),
        "total_fees": _money(total_fees),
        "active_clients": active_clients,
        "today_pnl": _money(today_pnl),
    }
