from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.client import Client


def _normalize_date(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    return value


class ClientRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: dict[str, Any]) -> Client:
        normalized = dict(payload)
        for key in ("join_date", "fee_start_date"):
            if key in normalized:
                normalized[key] = _normalize_date(normalized[key])
        client = Client(**normalized)
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def list_all(self):
        return self.db.query(Client).filter(Client.is_deleted.is_(False)).all()

    def get_by_id(self, client_id: str):
        return self.db.query(Client).filter(Client.id == client_id, Client.is_deleted.is_(False)).first()

    def update(self, client: Client, payload: dict[str, Any]) -> Client:
        normalized = dict(payload)
        for key in ("join_date", "fee_start_date"):
            if key in normalized:
                normalized[key] = _normalize_date(normalized[key])
        for key, value in normalized.items():
            setattr(client, key, value)
        self.db.commit()
        self.db.refresh(client)
        return client

    def soft_delete(self, client: Client) -> Client:
        client.is_deleted = True
        self.db.commit()
        self.db.refresh(client)
        return client
