from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class FundMovement(Base):
    __tablename__ = "fund_movements"

    id = Column(String, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False, index=True)
    movement_type = Column(String, nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    signed_amount = Column(Numeric(18, 2), nullable=False)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    client = relationship("Client", back_populates="fund_movements")
