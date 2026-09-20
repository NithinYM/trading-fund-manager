from typing import Any
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def snapshot(entity: Any) -> dict[str, Any]:
    return jsonable_encoder({column.key: getattr(entity, column.key) for column in inspect(entity).mapper.column_attrs})


def record_audit(
    db: Session,
    user: User,
    action: str,
    entity_type: str,
    entity_id: str,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            id=str(uuid4()),
            user_id=user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
        )
    )
    db.commit()