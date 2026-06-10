from __future__ import annotations

import os
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from infrastructure import crud_user, models
from infrastructure.db import SessionLocal
from services.jwt_service import decode_access_token

security = HTTPBearer()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

if ENVIRONMENT in ("prod", "production") and SECRET_KEY == "dev-secret-key":
    raise RuntimeError("CRITICAL: SECRET_KEY is not set securely for production environment.")

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> models.Utilisateur:
    token = credentials.credentials.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    try:
        payload = decode_access_token(token, SECRET_KEY)
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    user = crud_user.get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_admin(current_user: models.Utilisateur = Depends(get_current_user)) -> models.Utilisateur:
    if str(current_user.role) != "admin":  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user

def require_user(current_user: models.Utilisateur = Depends(get_current_user)) -> models.Utilisateur:
    if current_user.role not in ("admin", "user"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User privileges required")
    return current_user

