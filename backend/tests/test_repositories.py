from uuid import uuid4

from app.db.database import SessionLocal
from app.models.client import Client
from app.repositories.client_repository import ClientRepository


def test_client_repository_can_create_and_list():
    db = SessionLocal()
    try:
        repo = ClientRepository(db)
        client_id = str(uuid4())
        repo.create(
            {
                "id": client_id,
                "client_code": "C999",
                "name": "Repo Client",
                "opening_capital": 15000,
                "join_date": "2026-01-01",
                "status": "ACTIVE",
                "fee_type": "NONE",
                "fee_value": 0,
            }
        )

        created = repo.get_by_id(client_id)
        assert created is not None
        assert created.client_code == "C999"
    finally:
        db.rollback()
        db.close()
