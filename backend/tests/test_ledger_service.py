from datetime import date
from decimal import Decimal

from app.db.database import SessionLocal
from app.models.client import Client
from app.models.client_status_history import ClientStatusHistory
from app.models.daily_trading import DailyTrading
from app.models.fund_movement import FundMovement
from app.services.ledger_service import LedgerService


def test_recalculate_date_persists_workbook_aligned_ledger():
    trading_date = date(2026, 1, 2)
    with SessionLocal() as db:
        db.add_all(
            [
                Client(
                    id="ledger-active",
                    client_code="L001",
                    name="Active",
                    opening_capital=10000,
                    join_date=date(2026, 1, 1),
                    status="ACTIVE",
                    fee_type="PERCENTAGE",
                    fee_value=10,
                ),
                Client(
                    id="ledger-inactive",
                    client_code="L002",
                    name="Inactive",
                    opening_capital=5000,
                    join_date=date(2026, 1, 1),
                    status="INACTIVE",
                    fee_type="NONE",
                    fee_value=0,
                ),
                DailyTrading(
                    id="ledger-trading",
                    trading_date=trading_date,
                    gross_trading_pnl=1200,
                    transaction_charges=100,
                    net_pnl=1100,
                ),
                FundMovement(
                    id="ledger-movement",
                    date=trading_date,
                    client_id="ledger-active",
                    movement_type="DEPOSIT",
                    amount=1000,
                    signed_amount=1000,
                ),
                ClientStatusHistory(
                    id="ledger-status",
                    client_id="ledger-inactive",
                    status="INACTIVE",
                    from_date=date(2026, 1, 1),
                    to_date=date(2026, 12, 31),
                ),
            ]
        )
        db.commit()

        entries = LedgerService().recalculate_date_from_db(db, trading_date)

        active = next(entry for entry in entries if entry.client_id == "ledger-active")
        inactive = next(entry for entry in entries if entry.client_id == "ledger-inactive")
        assert active.capital_before_pnl == Decimal("11000.00")
        assert active.capital_share_percent == Decimal("100.000000")
        assert active.allocated_pnl == Decimal("1100.00")
        assert active.fee_debited == Decimal("110.00")
        assert active.closing_balance == Decimal("11990.00")
        assert inactive.allocated_pnl == Decimal("0.00")
