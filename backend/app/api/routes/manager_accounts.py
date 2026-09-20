from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.client_ledger import ClientLedger
from app.models.manager_account import ManagerAccount

router = APIRouter(prefix="/manager-accounts", tags=["manager-accounts"])


def _money(value: Decimal | None) -> str:
    return f"{value or Decimal('0.00'):.2f}"


@router.get("")
def list_manager_accounts(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    accounts = db.query(ManagerAccount).order_by(ManagerAccount.code.asc()).all()
    total_fees_received = db.query(ClientLedger).with_entities(
        func.coalesce(func.sum(ClientLedger.manager_fee_credit), Decimal("0.00")).label("fees_received")
    ).scalar() or Decimal("0.00")

    rows: list[dict[str, object]] = []
    for account in accounts:
        rows.append(
            {
                "id": account.id,
                "code": account.code,
                "name": account.name,
                "opening_capital": _money(account.opening_capital),
                "current_balance": _money(account.opening_capital + total_fees_received),
                "fees_received": _money(total_fees_received),
            }
        )
    return rows


@router.get("/{code}/reconciliation")
def get_manager_account_reconciliation(
    code: str,
    trading_date: date | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    account = db.query(ManagerAccount).filter(ManagerAccount.code == code).first()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager account not found")

    query = db.query(ClientLedger)
    if trading_date is not None:
        query = query.filter(ClientLedger.trading_date == trading_date)

    ledger = query.all()
    fees_received = sum((row.manager_fee_credit or Decimal("0.00") for row in ledger), Decimal("0.00"))
    expected_client_fees = sum((row.fee_debited or Decimal("0.00") for row in ledger), Decimal("0.00"))
    fee_transfer_delta = fees_received - expected_client_fees
    current_balance = account.opening_capital + fees_received

    return {
        "account_id": account.id,
        "code": account.code,
        "name": account.name,
        "opening_capital": _money(account.opening_capital),
        "fees_received": _money(fees_received),
        "expected_client_fees": _money(expected_client_fees),
        "fee_transfer_delta": _money(fee_transfer_delta),
        "current_balance": _money(current_balance),
        "fees_reconciled": fee_transfer_delta == Decimal("0.00"),
        "trading_date": trading_date.isoformat() if trading_date else None,
    }
