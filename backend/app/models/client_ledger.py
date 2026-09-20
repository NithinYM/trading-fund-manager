from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class ClientLedger(Base):
    __tablename__ = "client_ledger"

    id = Column(String, primary_key=True, index=True)
    trading_date = Column(Date, nullable=False, index=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False, index=True)
    fund_movement = Column(Numeric(18, 2), nullable=True, default=Decimal("0.00"))
    capital_before_pnl = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    capital_share_percent = Column(Numeric(18, 6), nullable=False, default=Decimal("0.000000"))
    net_daily_pnl = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    allocated_pnl = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    fee_debited = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    net_client_pnl = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    closing_balance = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    daily_return_percent = Column(Numeric(18, 6), nullable=True, default=Decimal("0.000000"))
    status_on_date = Column(String, nullable=False, default="ACTIVE")
    manager_fee_credit = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    calculation_version = Column(String, nullable=False, default="v1")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    client = relationship("Client", back_populates="ledger_entries")
