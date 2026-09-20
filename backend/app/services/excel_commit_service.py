from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any
from uuid import uuid4

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.client_ledger import ClientLedger
from app.models.client_status_history import ClientStatusHistory
from app.models.daily_trading import DailyTrading
from app.models.fund_movement import FundMovement
from app.services.calculation_engine import CalculationEngine
from app.services.excel_import_service import _find_header, _text
from app.services.ledger_service import LedgerService
from app.services.validation_service import ValidationService


def _date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip())


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value or "0"))


def _rows(workbook: Any, sheet_name: str) -> tuple[list[tuple[Any, ...]], dict[str, int]]:
    worksheet = workbook[sheet_name]
    values = list(worksheet.iter_rows(values_only=True))
    required = {
        "Clients": {"Client ID", "Client Name", "Opening Capital", "Join Date"},
        "Status History": {"Client ID", "Status", "From Date", "To Date"},
        "Fund Movements": {"Date", "Client ID", "Type", "Amount"},
        "Daily Trading": {"Date", "Gross Trading P&L", "Transaction Charges"},
        "Client Ledger": {"Date", "Client ID", "Capital Before P&L", "Allocated P&L", "Closing Balance (After Fee)"},
    }[sheet_name]
    header = _find_header(values, required)
    if header is None:
        raise ValueError(f"Required headers were not found in {sheet_name}")
    header_index, headers = header
    return values[header_index + 1 :], headers


def _value(row: tuple[Any, ...], headers: dict[str, int], name: str) -> Any:
    if name not in headers:
        return None
    index = headers[name]
    return row[index] if index < len(row) else None


def _normalize_nested_status_periods(periods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    periods_by_client: dict[str, list[dict[str, Any]]] = {}
    for period in periods:
        periods_by_client.setdefault(period["client_id"], []).append(period)

    for client_periods in periods_by_client.values():
        working = list(client_periods)
        for exception in sorted(client_periods, key=lambda period: (period["to_date"] - period["from_date"], period["from_date"])):
            updated: list[dict[str, Any]] = []
            for existing in working:
                contains_exception = (
                    existing is not exception
                    and existing["status"] != exception["status"]
                    and existing["from_date"] <= exception["from_date"]
                    and existing["to_date"] >= exception["to_date"]
                )
                if not contains_exception:
                    updated.append(existing)
                    continue
                if existing["from_date"] < exception["from_date"]:
                    updated.append({**existing, "to_date": exception["from_date"] - timedelta(days=1)})
                if exception["to_date"] < existing["to_date"]:
                    updated.append({**existing, "from_date": exception["to_date"] + timedelta(days=1)})
            working = updated
        normalized.extend(working)
    return normalized


class ExcelCommitService:
    @staticmethod
    def _import_ledger(workbook: Any, db: Session, client_ids: dict[str, str]) -> int:
        ledger_rows, ledger_headers = _rows(workbook, "Client Ledger")
        imported = 0
        db.query(ClientLedger).delete(synchronize_session=False)
        for row_number, row in enumerate(ledger_rows, start=4):
            trading_date = _value(row, ledger_headers, "Date")
            code = _text(_value(row, ledger_headers, "Client ID")).upper()
            if trading_date is None or not code:
                continue
            capital_before = _decimal(_value(row, ledger_headers, "Capital Before P&L"))
            allocated_pnl = _decimal(_value(row, ledger_headers, "Allocated P&L"))
            closing_balance = _decimal(_value(row, ledger_headers, "Closing Balance (After Fee)"))
            if code not in client_ids:
                if capital_before == 0 and allocated_pnl == 0 and closing_balance == 0:
                    continue
                raise ValueError(f"Client Ledger row {row_number}: unknown client {code}")
            fee_debited = _decimal(_value(row, ledger_headers, "Fee Debited"))
            net_client_pnl = _decimal(_value(row, ledger_headers, "Net Client P&L"))
            db.add(
                ClientLedger(
                    id=str(uuid4()),
                    trading_date=_date(trading_date),
                    client_id=client_ids[code],
                    fund_movement=_decimal(_value(row, ledger_headers, "Fund Movement")),
                    capital_before_pnl=capital_before,
                    capital_share_percent=_decimal(_value(row, ledger_headers, "Capital Share %")),
                    net_daily_pnl=_decimal(_value(row, ledger_headers, "Net Daily P&L")),
                    allocated_pnl=allocated_pnl,
                    fee_debited=fee_debited,
                    net_client_pnl=net_client_pnl if net_client_pnl else allocated_pnl - fee_debited,
                    closing_balance=closing_balance,
                    daily_return_percent=_decimal(_value(row, ledger_headers, "Daily Return %")),
                    status_on_date=_text(_value(row, ledger_headers, "Status on Date")).upper() or "ACTIVE",
                    manager_fee_credit=_decimal(_value(row, ledger_headers, "Manager Fee Credit")),
                    calculation_version="workbook-import",
                )
            )
            imported += 1
        return imported

    @staticmethod
    def import_workbook(content: bytes, db: Session) -> dict[str, int]:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        imported = {"clients": 0, "status_history": 0, "fund_movements": 0, "daily_trading": 0, "client_ledger": 0}
        client_ids: dict[str, str] = {}

        try:
            if "Clients" not in workbook.sheetnames:
                raise ValueError("Clients sheet is required")

            client_rows, client_headers = _rows(workbook, "Clients")
            for row_number, row in enumerate(client_rows, start=4):
                code = _text(_value(row, client_headers, "Client ID")).upper()
                name = _text(_value(row, client_headers, "Client Name"))
                if not code and not name:
                    continue
                if code and not name and not _value(row, client_headers, "Opening Capital") and not _value(row, client_headers, "Join Date"):
                    continue
                if not code or not name:
                    raise ValueError(f"Clients row {row_number}: Client ID and Client Name are required")

                existing = db.query(Client).filter(Client.client_code == code).first()
                if existing is None:
                    existing = Client(
                        id=str(uuid4()),
                        client_code=code,
                        name=name,
                        opening_capital=_decimal(_value(row, client_headers, "Opening Capital")),
                        join_date=_date(_value(row, client_headers, "Join Date")),
                        status=_text(_value(row, client_headers, "Current Status")).upper() or "ACTIVE",
                        fee_type=_text(_value(row, client_headers, "Fee Type")).upper() or "NONE",
                        fee_value=_decimal(_value(row, client_headers, "Fee Value")),
                    )
                    db.add(existing)
                    imported["clients"] += 1
                client_ids[code] = existing.id
            db.flush()

            if "Status History" in workbook.sheetnames:
                status_rows, status_headers = _rows(workbook, "Status History")
                periods = []
                for row_number, row in enumerate(status_rows, start=4):
                    code = _text(_value(row, status_headers, "Client ID")).upper()
                    status_value = _text(_value(row, status_headers, "Status")).upper()
                    from_date = _value(row, status_headers, "From Date")
                    to_date = _value(row, status_headers, "To Date")
                    if not code and not status_value:
                        continue
                    if not status_value and from_date is None and to_date is None:
                        continue
                    if code not in client_ids:
                        raise ValueError(f"Status History row {row_number}: unknown client {code}")
                    periods.append(
                        {
                            "client_id": code,
                            "status": status_value,
                            "from_date": _date(from_date),
                            "to_date": _date(to_date),
                        }
                    )
                periods = _normalize_nested_status_periods(periods)
                errors = ValidationService.validate_client_status_periods(periods)
                if errors:
                    raise ValueError("; ".join(errors))
                for row in periods:
                    db.add(
                        ClientStatusHistory(
                            id=str(uuid4()),
                            client_id=client_ids[row["client_id"]],
                            status="ACTIVE" if row.get("status") == "ACTIVE" else "INACTIVE",
                            from_date=row["from_date"],
                            to_date=row["to_date"],
                        )
                    )
                    imported["status_history"] += 1

            if "Fund Movements" in workbook.sheetnames:
                movement_rows, movement_headers = _rows(workbook, "Fund Movements")
                for row_number, row in enumerate(movement_rows, start=4):
                    code = _text(_value(row, movement_headers, "Client ID")).upper()
                    if not code and not _text(_value(row, movement_headers, "Type")):
                        continue
                    if code not in client_ids:
                        raise ValueError(f"Fund Movements row {row_number}: unknown client {code}")
                    movement_type = _text(_value(row, movement_headers, "Type")).upper()
                    amount = _decimal(_value(row, movement_headers, "Amount"))
                    errors = ValidationService.validate_fund_movement(amount, movement_type)
                    if errors:
                        raise ValueError(f"Fund Movements row {row_number}: {' '.join(errors)}")
                    db.add(
                        FundMovement(
                            id=str(uuid4()),
                            date=_date(_value(row, movement_headers, "Date")),
                            client_id=client_ids[code],
                            movement_type=movement_type,
                            amount=amount,
                            signed_amount=amount if movement_type == "DEPOSIT" else -amount,
                            remarks=_text(_value(row, movement_headers, "Remarks")) or None,
                        )
                    )
                    imported["fund_movements"] += 1

            if "Daily Trading" in workbook.sheetnames:
                trading_rows, trading_headers = _rows(workbook, "Daily Trading")
                engine = CalculationEngine()
                for row_number, row in enumerate(trading_rows, start=4):
                    trading_date = _value(row, trading_headers, "Date")
                    if trading_date is None:
                        continue
                    trading_date = _date(trading_date)
                    gross = _decimal(_value(row, trading_headers, "Gross Trading P&L"))
                    charges = _decimal(_value(row, trading_headers, "Transaction Charges"))
                    if db.query(DailyTrading).filter(DailyTrading.trading_date == trading_date).first() is not None:
                        raise ValueError(f"Daily Trading row {row_number}: duplicate trading date {trading_date}")
                    db.add(
                        DailyTrading(
                            id=str(uuid4()),
                            trading_date=trading_date,
                            gross_trading_pnl=gross,
                            transaction_charges=charges,
                            net_pnl=engine.calculate_daily_trading(gross, charges),
                            remarks=_text(_value(row, trading_headers, "Remarks")) or None,
                        )
                    )
                    imported["daily_trading"] += 1

            if "Client Ledger" in workbook.sheetnames:
                imported["client_ledger"] = ExcelCommitService._import_ledger(workbook, db, client_ids)
                db.commit()
            else:
                db.commit()
                trading_dates = [
                    row.trading_date
                    for row in db.query(DailyTrading.trading_date).order_by(DailyTrading.trading_date.asc()).all()
                ]
                ledger_service = LedgerService()
                for trading_date in trading_dates:
                    ledger_service.recalculate_date_from_db(db, trading_date)
            return imported
        except Exception:
            db.rollback()
            raise
        finally:
            workbook.close()
