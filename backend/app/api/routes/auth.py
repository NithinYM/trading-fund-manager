from datetime import datetime, timedelta, timezone
from hashlib import sha256

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _password_digest(password: str) -> bytes:
    return sha256(password.encode("utf-8")).digest()


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_password_digest(password), stored_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    valid_password = user is not None and _verify_password(payload.password, user.password_hash)
    if user is None or not user.is_active or not valid_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    token = jwt.encode(
        {"sub": user.id, "role": user.role, "exp": expires_at},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return LoginResponse(access_token=token, role=user.role)


@router.get("/me")
def current_user(user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"id": user.id, "username": user.username, "role": user.role}
