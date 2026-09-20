from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.client_status_history import ClientStatusHistory


def _normalize_date(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    return value


class StatusHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: dict[str, Any]) -> ClientStatusHistory:
        normalized = dict(payload)
        for key in ("from_date", "to_date"):
            if key in normalized:
                normalized[key] = _normalize_date(normalized[key])
        status_record = ClientStatusHistory(**normalized)
        self.db.add(status_record)
        self.db.commit()
        self.db.refresh(status_record)
        return status_record

    def list_all(self):
        return self.db.query(ClientStatusHistory).all()
