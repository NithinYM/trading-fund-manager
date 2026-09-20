from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class FundMovementBase(BaseModel):
    date: date
    client_id: str
    movement_type: str
    amount: Decimal = Field(gt=0)
    remarks: Optional[str] = None


class FundMovementCreate(FundMovementBase):
    pass


class FundMovementUpdate(FundMovementBase):
    pass


class FundMovementRead(FundMovementBase):
    id: str
    signed_amount: Decimal

    model_config = {"from_attributes": True}
