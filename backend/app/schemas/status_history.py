from datetime import date
from typing import Optional

from pydantic import BaseModel


class StatusHistoryBase(BaseModel):
    client_id: str
    status: str
    from_date: date
    to_date: date
    remarks: Optional[str] = None


class StatusHistoryCreate(StatusHistoryBase):
    pass


class StatusHistoryUpdate(StatusHistoryBase):
    pass


class StatusHistoryRead(StatusHistoryBase):
    id: str

    model_config = {"from_attributes": True}
