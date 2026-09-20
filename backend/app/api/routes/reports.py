from datetime import date
from decimal import Decimal
from csv import writer
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.client_ledger import ClientLedger
from app.models.daily_trading import DailyTrading
from app.services.ledger_service import LedgerService
from app.services.audit_service import record_audit

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily")
def daily_report(trading_date: date, db: Session = Depends(get_db)) -> dict[str, object]:
    trading = db.query(DailyTrading).filter(DailyTrading.trading_date == trading_date).first()
    if trading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading record not found")
    ledger = db.query(ClientLedger).filter(ClientLedger.trading_date == trading_date).all()
    return {
        "trading_date": trading_date,
        "gross_trading_pnl": _money(trading.gross_trading_pnl),
        "transaction_charges": _money(trading.transaction_charges),
        "net_pnl": _money(trading.net_pnl),
        "allocated_pnl": _money(sum((row.allocated_pnl or Decimal("0.00") for row in ledger), Decimal("0.00"))),
        "fees": _money(sum((row.fee_debited or Decimal("0.00") for row in ledger), Decimal("0.00"))),
        "ledger_entries": len(ledger),
    }


@router.get("/daily/export")
def export_daily_report(trading_date: date, db: Session = Depends(get_db)) -> StreamingResponse:
    trading = db.query(DailyTrading).filter(DailyTrading.trading_date == trading_date).first()
    if trading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading record not found")
    ledger = db.query(ClientLedger).filter(ClientLedger.trading_date == trading_date).all()
    output = StringIO()
    csv_writer = writer(output)
    csv_writer.writerow(["trading_date", "gross_trading_pnl", "transaction_charges", "net_pnl"])
    csv_writer.writerow([trading_date.isoformat(), _money(trading.gross_trading_pnl), _money(trading.transaction_charges), _money(trading.net_pnl)])
    csv_writer.writerow([])
    csv_writer.writerow(["client_id", "capital_before_pnl", "allocated_pnl", "fee_debited", "net_client_pnl", "closing_balance", "status_on_date"])
    for row in ledger:
        csv_writer.writerow([row.client_id, _money(row.capital_before_pnl), _money(row.allocated_pnl), _money(row.fee_debited), _money(row.net_client_pnl), _money(row.closing_balance), row.status_on_date])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="daily-report-{trading_date.isoformat()}.csv"'})


@router.get("/monthly")
def monthly_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    trading = db.query(DailyTrading).filter(DailyTrading.trading_date >= start, DailyTrading.trading_date < end).all()
    ledger = db.query(ClientLedger).filter(ClientLedger.trading_date >= start, ClientLedger.trading_date < end).all()
    return {
        "year": year,
        "month": month,
        "trading_days": len(trading),
        "gross_trading_pnl": _money(sum((row.gross_trading_pnl or Decimal("0.00") for row in trading), Decimal("0.00"))),
        "transaction_charges": _money(sum((row.transaction_charges or Decimal("0.00") for row in trading), Decimal("0.00"))),
        "net_pnl": _money(sum((row.net_pnl or Decimal("0.00") for row in trading), Decimal("0.00"))),
        "allocated_pnl": _money(sum((row.allocated_pnl or Decimal("0.00") for row in ledger), Decimal("0.00"))),
        "fees": _money(sum((row.fee_debited or Decimal("0.00") for row in ledger), Decimal("0.00"))),
    }


@router.get("/monthly/export")
def export_monthly_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    trading = db.query(DailyTrading).filter(DailyTrading.trading_date >= start, DailyTrading.trading_date < end).all()
    ledger = db.query(ClientLedger).filter(ClientLedger.trading_date >= start, ClientLedger.trading_date < end).all()
    output = StringIO()
    csv_writer = writer(output)
    csv_writer.writerow(["year", "month", "trading_days", "gross_trading_pnl", "transaction_charges", "net_pnl", "allocated_pnl", "fees"])
    csv_writer.writerow([year, month, len(trading), _money(sum((row.gross_trading_pnl or Decimal("0.00") for row in trading), Decimal("0.00"))), _money(sum((row.transaction_charges or Decimal("0.00") for row in trading), Decimal("0.00"))), _money(sum((row.net_pnl or Decimal("0.00") for row in trading), Decimal("0.00"))), _money(sum((row.allocated_pnl or Decimal("0.00") for row in ledger), Decimal("0.00"))), _money(sum((row.fee_debited or Decimal("0.00") for row in ledger), Decimal("0.00")))])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="monthly-report-{year}-{month:02d}.csv"'})


@router.post("/recalculate/{trading_date}")
def recalculate_report(
    trading_date: date,
    db: Session = Depends(get_db),
    user=Depends(require_roles("ADMIN", "MANAGER")),
) -> dict[str, object]:
    try:
        entries = LedgerService().recalculate_date_from_db(db, trading_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    record_audit(db, user, "RECALCULATE", "CLIENT_LEDGER", trading_date.isoformat(), new_values={"trading_date": trading_date.isoformat(), "entries": len(entries)})
    return {
        "trading_date": trading_date,
        "entries": [
            {
                "id": entry.id,
                "client_id": entry.client_id,
                "allocated_pnl": entry.allocated_pnl,
                "fee_debited": entry.fee_debited,
                "closing_balance": entry.closing_balance,
                "status_on_date": entry.status_on_date,
            }
            for entry in entries
        ],
    }


@router.get("/reconciliation/{trading_date}")
def reconciliation_report(trading_date: date, db: Session = Depends(get_db)) -> dict[str, object]:
    trading = db.query(DailyTrading).filter(DailyTrading.trading_date == trading_date).first()
    if trading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading record not found")
    ledger = db.query(ClientLedger).filter(ClientLedger.trading_date == trading_date).all()
    allocated = sum((row.allocated_pnl or Decimal("0.00") for row in ledger), Decimal("0.00"))
    fees = sum((row.fee_debited or Decimal("0.00") for row in ledger), Decimal("0.00"))
    manager_credits = sum((row.manager_fee_credit or Decimal("0.00") for row in ledger), Decimal("0.00"))
    allocation_delta = trading.net_pnl - allocated
    fee_transfer_delta = fees - manager_credits
    return {
        "trading_date": trading_date,
        "net_pnl": _money(trading.net_pnl),
        "allocated_pnl": _money(allocated),
        "allocation_delta": _money(allocation_delta),
        "total_client_fees": _money(fees),
        "manager_fee_credits": _money(manager_credits),
        "fee_transfer_delta": _money(fee_transfer_delta),
        "allocation_reconciled": allocation_delta == Decimal("0.00"),
        "fees_reconciled": fee_transfer_delta == Decimal("0.00"),
    }


def _money(value: Decimal | None) -> str:
    return f"{value or Decimal('0.00'):.2f}"
