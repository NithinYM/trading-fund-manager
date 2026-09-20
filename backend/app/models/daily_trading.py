from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Date, DateTime, Numeric, String, Text

from app.db.database import Base


class DailyTrading(Base):
    __tablename__ = "daily_trading"

    id = Column(String, primary_key=True, index=True)
    trading_date = Column(Date, nullable=False, unique=True, index=True)
    gross_trading_pnl = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    transaction_charges = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    net_pnl = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
