from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models.client_ledger import ClientLedger
from app.models.client import Client
from app.models.client_status_history import ClientStatusHistory
from app.models.daily_trading import DailyTrading
from app.models.fund_movement import FundMovement
from app.repositories.daily_trading_repository import DailyTradingRepository
from app.schemas.daily_trading import DailyTradingCreate, DailyTradingRead
from app.services.calculation_engine import CalculationEngine
from app.services.audit_service import record_audit, snapshot

router = APIRouter(prefix="/trading", tags=["trading"])


def _money(value: Decimal | None) -> str:
    return f"{value or Decimal('0.00'):.2f}"


@router.get("", response_model=list[DailyTradingRead])
def list_trading(db: Session = Depends(get_db)) -> list[DailyTradingRead]:
    return DailyTradingRepository(db).list_all()


@router.get("/{trading_date}/allocation")
def get_allocation(trading_date: date, db: Session = Depends(get_db), _user=Depends(get_current_user)) -> dict[str, object]:
    trading = db.query(DailyTrading).filter(DailyTrading.trading_date == trading_date).first()
    if trading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading record not found")

    engine = CalculationEngine()
    clients = db.query(Client).filter(Client.is_deleted.is_(False)).all()
    active_clients: list[Client] = []
    capital_by_client: dict[str, Decimal] = {}

    for client in clients:
        history = (
            db.query(ClientStatusHistory)
            .filter(
                ClientStatusHistory.client_id == client.id,
                ClientStatusHistory.from_date <= trading_date,
                ClientStatusHistory.to_date >= trading_date,
            )
            .order_by(ClientStatusHistory.from_date.desc())
            .all()
        )
        status = history[0].status if history else client.status
        if status != "ACTIVE":
            continue

        signed_movements = sum(
            (movement.signed_amount for movement in client.fund_movements if movement.date <= trading_date),
            Decimal("0.00"),
        )
        capital_before = Decimal(str(client.opening_capital or "0.00")) + signed_movements
        capital_by_client[client.id] = capital_before
        active_clients.append(client)

    if not capital_by_client:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot calculate allocation because no active clients exist for this date.")

    total_active_capital = sum(capital_by_client.values(), Decimal("0.00"))
    allocations = engine.calculate_proportional_allocations(Decimal(str(trading.net_pnl or "0.00")), capital_by_client)
    entries: list[dict[str, object]] = []
    total_fees = Decimal("0.00")
    allocated_total = Decimal("0.00")

    for client in active_clients:
        capital_before = capital_by_client[client.id]
        allocated_pnl = allocations.get(client.id, Decimal("0.00"))
        fee = Decimal("0.00")
        if client.fee_type != "NONE" and (client.fee_start_date is None or client.fee_start_date <= trading_date):
            fee = engine.calculate_client_fee(allocated_pnl, client.fee_type, Decimal(str(client.fee_value or "0.00")))
        closing_balance = engine.calculate_closing_balance(capital_before, Decimal("0.00"), Decimal("0.00"), allocated_pnl, fee)
        share_percent = (capital_before / total_active_capital) * Decimal("100")
        total_fees += fee
        allocated_total += allocated_pnl
        entries.append(
            {
                "client_id": client.id,
                "client_code": client.client_code,
                "client_name": client.name,
                "capital": _money(capital_before),
                "share_percent": _money(share_percent),
                "allocated_pnl": _money(allocated_pnl),
                "fee": _money(fee),
                "net_pnl": _money(allocated_pnl - fee),
                "closing_balance": _money(closing_balance),
            }
        )

    allocation_difference = Decimal(str(trading.net_pnl or "0.00")) - allocated_total
    return {
        "trading_date": trading_date.isoformat(),
        "active_capital": _money(total_active_capital),
        "active_clients": len(active_clients),
        "net_pnl": _money(trading.net_pnl),
        "allocated_pnl": _money(allocated_total),
        "total_fees": _money(total_fees),
        "manager_fee": _money(total_fees),
        "allocation_difference": _money(allocation_difference),
        "entries": entries,
    }


@router.post("", response_model=DailyTradingRead)
def create_trading(
    payload: DailyTradingCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("ADMIN")),
) -> DailyTradingRead:
    repository = DailyTradingRepository(db)
    if repository.get_by_date(payload.trading_date) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trading record already exists for this date")

    data = payload.model_dump()
    data["id"] = str(uuid4())
    data["net_pnl"] = CalculationEngine().calculate_daily_trading(
        data["gross_trading_pnl"],
        data["transaction_charges"],
    )
    trading = repository.create(data)
    record_audit(db, user, "CREATE", "DAILY_TRADING", trading.id, new_values=snapshot(trading))
    return trading


@router.delete("/{trading_date}")
def delete_trading(
    trading_date: date,
    db: Session = Depends(get_db),
    user=Depends(require_roles("ADMIN")),
) -> dict[str, str]:
    trading = db.query(DailyTrading).filter(DailyTrading.trading_date == trading_date).first()
    if trading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading record not found")
    latest = db.query(DailyTrading).order_by(DailyTrading.trading_date.desc()).first()
    if latest is None or latest.id != trading.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only the latest daily trading result can be deleted to preserve historical ledger integrity",
        )
    old_values = snapshot(trading)
    db.query(ClientLedger).filter(ClientLedger.trading_date == trading_date).delete(synchronize_session=False)
    db.delete(trading)
    db.commit()
    record_audit(db, user, "DELETE", "DAILY_TRADING", trading.id, old_values=old_values)
    return {"status": "deleted", "trading_date": trading_date.isoformat()}
