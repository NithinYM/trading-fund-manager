from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(String, primary_key=True, index=True)
    client_code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    opening_capital = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    join_date = Column(Date, nullable=False)
    contact = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE")
    fee_type = Column(String, nullable=False, default="NONE")
    fee_value = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    fee_basis = Column(String, nullable=True)
    fee_start_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_deleted = Column(Boolean, default=False, nullable=False)

    status_history = relationship("ClientStatusHistory", back_populates="client")
    fund_movements = relationship("FundMovement", back_populates="client")
    ledger_entries = relationship("ClientLedger", back_populates="client")
