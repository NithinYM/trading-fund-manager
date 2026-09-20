from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models.client_ledger import ClientLedger
from app.models.client_status_history import ClientStatusHistory
from app.models.fund_movement import FundMovement
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientRead
from app.services.audit_service import record_audit, snapshot

router = APIRouter(prefix="/clients", tags=["clients"])


def _money(value: Decimal | None) -> str:
    return f"{value or Decimal('0.00'):.2f}"


@router.get("", response_model=list[ClientRead])
def list_clients(db: Session = Depends(get_db)) -> list[ClientRead]:
    repo = ClientRepository(db)
    clients = repo.list_all()
    rows: list[ClientRead] = []
    for client in clients:
        latest_ledger = (
            db.query(ClientLedger)
            .filter(ClientLedger.client_id == client.id)
            .order_by(ClientLedger.trading_date.desc())
            .first()
        )
        movement_total = sum((movement.signed_amount for movement in client.fund_movements), Decimal("0.00"))
        current_balance = latest_ledger.closing_balance if latest_ledger else Decimal(str(client.opening_capital or "0.00")) + movement_total
        rows.append(ClientRead.model_validate(client).model_copy(update={"current_balance": current_balance}))
    return rows


@router.post("", response_model=ClientRead, status_code=status.HTTP_200_OK)
def create_client(payload: ClientCreate, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN"))) -> ClientRead:
    repo = ClientRepository(db)
    data = payload.model_dump()
    data["id"] = str(uuid4())
    try:
        client = repo.create(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_audit(db, user, "CREATE", "CLIENT", client.id, new_values=snapshot(client))
    return client


@router.get("/{client_id}/detail")
def get_client_detail(client_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)) -> dict[str, object]:
    repo = ClientRepository(db)
    client = repo.get_by_id(client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    movements = (
        db.query(FundMovement)
        .filter(FundMovement.client_id == client_id)
        .order_by(FundMovement.date.asc(), FundMovement.created_at.asc())
        .all()
    )
    ledger_rows = (
        db.query(ClientLedger)
        .filter(ClientLedger.client_id == client_id)
        .order_by(ClientLedger.trading_date.asc())
        .all()
    )

    total_contributed = sum((movement.signed_amount for movement in movements if movement.signed_amount > 0), Decimal("0.00"))
    total_withdrawn = sum((abs(movement.signed_amount) for movement in movements if movement.signed_amount < 0), Decimal("0.00"))
    total_allocated_pnl = sum((entry.allocated_pnl or Decimal("0.00") for entry in ledger_rows), Decimal("0.00"))
    total_fees = sum((entry.fee_debited or Decimal("0.00") for entry in ledger_rows), Decimal("0.00"))
    current_capital = (
        ledger_rows[-1].closing_balance
        if ledger_rows
        else Decimal(str(client.opening_capital or "0.00")) + total_contributed - total_withdrawn
    )
    net_pnl = total_allocated_pnl - total_fees
    status_rows = (
        db.query(ClientStatusHistory)
        .filter(ClientStatusHistory.client_id == client_id)
        .order_by(ClientStatusHistory.from_date.asc())
        .all()
    )
    status = status_rows[-1] if status_rows else None
    current_status = status.status if status else client.status
    opening_base = Decimal(str(client.opening_capital or "0.00"))
    effective_capital = opening_base + total_contributed - total_withdrawn
    overall_return_pct = (
        (current_capital - effective_capital) / effective_capital * Decimal("100")
        if effective_capital != 0
        else Decimal("0.00")
    )
    manager_fee_credit_total = sum((entry.manager_fee_credit or Decimal("0.00") for entry in ledger_rows), Decimal("0.00"))
    fee_transfer_delta = total_fees - manager_fee_credit_total

    return {
        "client": {
            "id": client.id,
            "client_code": client.client_code,
            "name": client.name,
            "status": client.status,
            "fee_type": client.fee_type,
            "fee_value": _money(client.fee_value),
            "join_date": client.join_date.isoformat() if client.join_date else None,
        },
        "summary": {
            "current_capital": _money(current_capital),
            "total_contributed": _money(total_contributed),
            "total_withdrawn": _money(total_withdrawn),
            "total_allocated_pnl": _money(total_allocated_pnl),
            "total_fees": _money(total_fees),
            "manager_fee_credit_total": _money(manager_fee_credit_total),
            "fee_transfer_delta": _money(fee_transfer_delta),
            "net_pnl": _money(net_pnl),
            "overall_return_pct": _money(overall_return_pct),
            "current_status": current_status,
        },
        "status_history": [
            {
                "id": row.id,
                "status": row.status,
                "from_date": row.from_date.isoformat(),
                "to_date": row.to_date.isoformat(),
                "remarks": row.remarks,
            }
            for row in status_rows
        ],
        "ledger": [
            {
                "trading_date": entry.trading_date.isoformat(),
                "fund_movement": _money(entry.fund_movement),
                "capital_before_pnl": _money(entry.capital_before_pnl),
                "allocated_pnl": _money(entry.allocated_pnl),
                "fee_debited": _money(entry.fee_debited),
                "manager_fee_credit": _money(entry.manager_fee_credit),
                "closing_balance": _money(entry.closing_balance),
                "daily_return_percent": _money(entry.daily_return_percent),
                "net_client_pnl": _money(entry.net_client_pnl),
                "status_on_date": entry.status_on_date,
            }
            for entry in ledger_rows
        ],
    }


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: str, db: Session = Depends(get_db)) -> ClientRead:
    repo = ClientRepository(db)
    client = repo.get_by_id(client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=ClientRead)
def update_client(client_id: str, payload: ClientCreate, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN"))) -> ClientRead:
    repo = ClientRepository(db)
    client = repo.get_by_id(client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    old_values = snapshot(client)
    updated = repo.update(client, payload.model_dump())
    record_audit(db, user, "UPDATE", "CLIENT", updated.id, old_values, snapshot(updated))
    return updated


@router.delete("/{client_id}")
def delete_client(client_id: str, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN"))) -> dict[str, str]:
    repo = ClientRepository(db)
    client = repo.get_by_id(client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    old_values = snapshot(client)
    repo.soft_delete(client)
    record_audit(db, user, "DELETE", "CLIENT", client.id, old_values, snapshot(client))
    return {"status": "deleted", "client_id": client_id}
