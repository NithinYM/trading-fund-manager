from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class DailyTradingBase(BaseModel):
    trading_date: date
    gross_trading_pnl: Decimal = Field(default=Decimal("0.00"))
    transaction_charges: Decimal = Field(default=Decimal("0.00"))
    net_pnl: Decimal = Field(default=Decimal("0.00"))
    remarks: Optional[str] = None


class DailyTradingCreate(DailyTradingBase):
    pass


class DailyTradingUpdate(DailyTradingBase):
    pass


class DailyTradingRead(DailyTradingBase):
    id: str

    model_config = {"from_attributes": True}
