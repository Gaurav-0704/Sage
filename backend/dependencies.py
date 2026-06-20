"""
Shared FastAPI dependencies — v0.5 role model.

Roles: owner | staff | teacher | student
A teacher with `can_do_front_office=True` is allowed to do tile-driven
payment / expense entry, alongside owner and staff.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import auth
import models
from database import SessionLocal


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = auth.decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.status != "active":
        raise HTTPException(status_code=403, detail=f"Account is {user.status}")
    return user


def require_owner(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Owner access required.")
    return user


def require_teacher(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required.")
    return user


def require_student(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access required.")
    return user


def require_staff_or_owner(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role not in ("staff", "owner"):
        raise HTTPException(status_code=403, detail="Staff or Owner access required.")
    return user


def require_can_collect(user: models.User = Depends(get_current_user)) -> models.User:
    """Owner, Staff, or Teacher with front-office flag — anyone allowed at the tile UI."""
    if user.role in ("owner", "staff"):
        return user
    if user.role == "teacher" and user.can_do_front_office:
        return user
    raise HTTPException(status_code=403, detail="Front-office access required.")


def require_school_member(user: models.User = Depends(get_current_user)) -> models.User:
    """Anyone signed in (owner|staff|teacher|student)."""
    if user.role not in ("owner", "staff", "teacher", "student"):
        raise HTTPException(status_code=403, detail="Sign-in required.")
    return user
