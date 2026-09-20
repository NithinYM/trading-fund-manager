from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.fund_movement import FundMovement


def _normalize_date(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    return value


class FundMovementRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: dict[str, Any]) -> FundMovement:
        normalized = dict(payload)
        if "date" in normalized:
            normalized["date"] = _normalize_date(normalized["date"])
        movement = FundMovement(**normalized)
        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def list_all(self):
        return self.db.query(FundMovement).order_by(FundMovement.date.asc()).all()
