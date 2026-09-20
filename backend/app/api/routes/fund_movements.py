from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.repositories.client_repository import ClientRepository
from app.repositories.fund_movement_repository import FundMovementRepository
from app.schemas.fund_movement import FundMovementCreate, FundMovementRead
from app.services.validation_service import ValidationService
from app.services.audit_service import record_audit, snapshot

router = APIRouter(prefix="/fund-movements", tags=["fund-movements"])


@router.get("", response_model=list[FundMovementRead])
def list_fund_movements(db: Session = Depends(get_db)) -> list[FundMovementRead]:
    return FundMovementRepository(db).list_all()


@router.post("", response_model=FundMovementRead)
def create_fund_movement(
    payload: FundMovementCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("ADMIN")),
) -> FundMovementRead:
    if ClientRepository(db).get_by_id(payload.client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    errors = ValidationService.validate_fund_movement(payload.amount, payload.movement_type)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors)

    signed_amount = payload.amount if payload.movement_type == "DEPOSIT" else -payload.amount
    data = payload.model_dump()
    data["id"] = str(uuid4())
    data["signed_amount"] = signed_amount
    movement = FundMovementRepository(db).create(data)
    record_audit(db, user, "CREATE", "FUND_MOVEMENT", movement.id, new_values=snapshot(movement))
    return movement
