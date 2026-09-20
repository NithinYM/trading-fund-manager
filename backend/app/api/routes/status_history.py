from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.repositories.client_repository import ClientRepository
from app.repositories.status_history_repository import StatusHistoryRepository
from app.schemas.status_history import StatusHistoryCreate, StatusHistoryRead
from app.services.validation_service import ValidationService
from app.services.audit_service import record_audit, snapshot

router = APIRouter(prefix="/status-history", tags=["status-history"])


@router.get("", response_model=list[StatusHistoryRead])
def list_status_history(db: Session = Depends(get_db)) -> list[StatusHistoryRead]:
    return StatusHistoryRepository(db).list_all()


@router.post("", response_model=StatusHistoryRead)
def create_status_history(
    payload: StatusHistoryCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("ADMIN")),
) -> StatusHistoryRead:
    if ClientRepository(db).get_by_id(payload.client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    repository = StatusHistoryRepository(db)
    periods = [
        {
            "client_id": item.client_id,
            "from_date": item.from_date,
            "to_date": item.to_date,
        }
        for item in repository.list_all()
    ]
    periods.append(payload.model_dump())
    errors = ValidationService.validate_client_status_periods(periods)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors)

    data = payload.model_dump()
    data["id"] = str(uuid4())
    status_history = repository.create(data)
    record_audit(db, user, "CREATE", "CLIENT_STATUS_HISTORY", status_history.id, new_values=snapshot(status_history))
    return status_history
