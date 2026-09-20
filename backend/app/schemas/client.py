from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    client_code: str
    name: str
    opening_capital: Decimal = Field(default=Decimal("0.00"))
    join_date: date
    contact: Optional[str] = None
    notes: Optional[str] = None
    status: str = "ACTIVE"
    fee_type: str = "NONE"
    fee_value: Decimal = Field(default=Decimal("0.00"))
    fee_basis: Optional[str] = None
    fee_start_date: Optional[date] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(ClientBase):
    pass


class ClientRead(ClientBase):
    id: str
    current_balance: Decimal | None = None

    model_config = {"from_attributes": True}
