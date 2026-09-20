from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.daily_trading import DailyTrading


def _normalize_date(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    return value


class DailyTradingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: dict[str, Any]) -> DailyTrading:
        normalized = dict(payload)
        if "trading_date" in normalized:
            normalized["trading_date"] = _normalize_date(normalized["trading_date"])
        record = DailyTrading(**normalized)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_date(self, trading_date: date):
        return self.db.query(DailyTrading).filter(DailyTrading.trading_date == trading_date).first()

    def list_all(self):
        return self.db.query(DailyTrading).order_by(DailyTrading.trading_date.asc()).all()
