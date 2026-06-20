"""
Auth Agent — v0.5.

Adds: signup with role picker (with owner approval queue), forgot/reset
password with email-delivered 6-digit code, owner approval endpoints.
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import auth
import models
import notifications
import schemas
from dependencies import get_db, get_current_user, require_owner

router = APIRouter(prefix="/auth", tags=["auth"])

CODE_TTL_MIN = 15
SCHOOL_NAME = "Sage"


# ---------------- Login ---------------- #

@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not auth.verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.status == "pending":
        raise HTTPException(
            status_code=403,
            detail="Your account is pending approval by an Owner.")
    if user.status == "disabled":
        raise HTTPException(status_code=403, detail="This account has been disabled.")
    token = auth.create_access_token({"sub": str(user.id), "role": user.role})
    return schemas.TokenOut(
        access_token=token,
        user=schemas.UserOut.model_validate(user),
    )


# ---------------- Signup ---------------- #

@router.post("/signup")
def signup(payload: schemas.SignupIn, db: Session = Depends(get_db)):
    """
    Self-signup. Owner cannot self-signup.
        - Student: must provide a matching admission_no — auto-activated.
        - Staff / Teacher: created as pending, must be approved by Owner.
    """
    if payload.role == "owner":
        raise HTTPException(403, "Owner accounts cannot be self-registered.")
    if payload.role not in ("staff", "teacher", "student"):
        raise HTTPException(400, "role must be staff, teacher, or student")

    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(400, "An account with this email already exists.")
    if len(payload.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")

    if payload.role == "student":
        if not payload.admission_no:
            raise HTTPException(400, "Students must provide their admission number.")
        student = db.query(models.Student).filter(
            models.Student.admission_no == payload.admission_no.strip()
        ).first()
        if not student:
            raise HTTPException(400, "No student record found with that admission number.")
        if student.user_id:
            raise HTTPException(400, "This student already has a login. Use Forgot Password if needed.")

        user = models.User(
            name=payload.name, email=payload.email,
            password=auth.hash_password(payload.password),
            role="student", status="active",
        )
        db.add(user); db.commit(); db.refresh(user)
        student.user_id = user.id
        db.commit()
        notifications.send(db, payload.email,
            f"Welcome to {SCHOOL_NAME}",
            f"Hi {payload.name},\n\nYour student login is ready. "
            f"Sign in with your email and password to see your assignments and marks.\n\n"
            f"— {SCHOOL_NAME}")
        return {"ok": True, "status": "active",
                "message": "Account created. You can sign in now."}

    if payload.role == "teacher":
        if not payload.employee_id:
            raise HTTPException(400, "Teachers must provide an employee id.")
        if db.query(models.Teacher).filter(
            models.Teacher.employee_id == payload.employee_id.strip()
        ).first():
            raise HTTPException(400, "This employee id is already registered.")

    user = models.User(
        name=payload.name, email=payload.email,
        password=auth.hash_password(payload.password),
        role=payload.role, status="pending",
    )
    db.add(user); db.commit(); db.refresh(user)

    if payload.role == "teacher":
        t = models.Teacher(
            user_id=user.id,
            employee_id=payload.employee_id.strip(),
            subject=payload.subject,
            classes_taught=payload.classes_taught,
            qualification=payload.qualification,
            phone=payload.phone,
        )
        db.add(t); db.commit()

    # Notify all owners.
    owners = db.query(models.User).filter(models.User.role == "owner",
                                          models.User.status == "active").all()
    for ow in owners:
        notifications.send(db, ow.email,
            f"New {payload.role} signup pending — {payload.name}",
            f"{payload.name} ({payload.email}) signed up as a {payload.role}.\n"
            f"Sign in to {SCHOOL_NAME} ERP and visit the Approvals page to review.")

    return {"ok": True, "status": "pending",
            "message": "Account created and is awaiting approval by an Owner."}


# ---------------- Approvals (Owner) ---------------- #

@router.get("/pending", response_model=list[schemas.UserOut])
def list_pending(db: Session = Depends(get_db),
                 _owner: models.User = Depends(require_owner)):
    return db.query(models.User).filter(models.User.status == "pending") \
        .order_by(models.User.id).all()


@router.post("/users/{user_id}/approve", response_model=schemas.UserOut)
def approve_user(user_id: int,
                 payload: schemas.ApprovalAction,
                 db: Session = Depends(get_db),
                 _owner: models.User = Depends(require_owner)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")
    u.status = "active"
    if payload.can_do_front_office is not None and u.role == "teacher":
        u.can_do_front_office = payload.can_do_front_office
    db.commit(); db.refresh(u)
    notifications.send(db, u.email,
        f"Your {SCHOOL_NAME} account is now active",
        f"Hi {u.name},\n\nYour account has been approved. Sign in any time.\n\n— {SCHOOL_NAME}")
    return u


@router.post("/users/{user_id}/reject")
def reject_user(user_id: int,
                db: Session = Depends(get_db),
                _owner: models.User = Depends(require_owner)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u: raise HTTPException(404, "User not found")
    if u.role == "teacher":
        t = db.query(models.Teacher).filter(models.Teacher.user_id == u.id).first()
        if t: db.delete(t)
    db.delete(u)
    db.commit()
    return {"ok": True}


# ---------------- Forgot / reset password ---------------- #

@router.post("/forgot")
def forgot_password(payload: schemas.ForgotIn, db: Session = Depends(get_db)):
    """Generate + email a 6-digit code. Always returns 200 (don't leak existence)."""
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user:
        # Invalidate any prior unused codes.
        for c in db.query(models.PasswordResetCode).filter(
            models.PasswordResetCode.user_id == user.id,
            models.PasswordResetCode.used == False,
        ).all():
            c.used = True
        code = f"{secrets.randbelow(1_000_000):06d}"
        rec = models.PasswordResetCode(
            user_id=user.id, code=code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=CODE_TTL_MIN),
        )
        db.add(rec); db.commit()
        notifications.send(db, user.email,
            f"Your {SCHOOL_NAME} verification code",
            f"Your password-reset code is: {code}\n\n"
            f"It expires in {CODE_TTL_MIN} minutes.\n\nIf you didn't ask for this, you can ignore this email.")
    return {"ok": True,
            "message": "If that email exists, a verification code has been sent."}


@router.post("/reset")
def reset_password(payload: schemas.ResetIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(400, "Invalid code or email.")
    if len(payload.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters.")

    rec = db.query(models.PasswordResetCode).filter(
        models.PasswordResetCode.user_id == user.id,
        models.PasswordResetCode.code == payload.code.strip(),
        models.PasswordResetCode.used == False,
    ).order_by(models.PasswordResetCode.id.desc()).first()
    if not rec:
        raise HTTPException(400, "Invalid code.")

    expires_at = rec.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(400, "Code has expired. Request a new one.")

    rec.used = True
    user.password = auth.hash_password(payload.new_password)
    db.commit()
    return {"ok": True, "message": "Password updated. You can sign in now."}


# ---------------- /me ---------------- #

@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=schemas.UserOut)
def update_me(payload: schemas.UserUpdate,
              user: models.User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    if payload.name:
        user.name = payload.name
    if payload.email:
        if db.query(models.User).filter(models.User.email == payload.email,
                                        models.User.id != user.id).first():
            raise HTTPException(400, "Email already in use")
        user.email = payload.email
    db.commit(); db.refresh(user)
    return user


@router.put("/me/password")
def change_password(payload: schemas.PasswordChange,
                    user: models.User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not auth.verify_password(payload.old_password, user.password):
        raise HTTPException(400, "Current password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters")
    user.password = auth.hash_password(payload.new_password)
    db.commit()
    return {"ok": True, "message": "Password updated"}


# ---------------- User admin (Owner) ---------------- #

@router.post("/users", response_model=schemas.UserOut)
def create_user(payload: schemas.UserCreate,
                db: Session = Depends(get_db),
                _owner: models.User = Depends(require_owner)):
    if payload.role not in ("owner", "staff", "teacher", "student"):
        raise HTTPException(status_code=400, detail="invalid role")
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        name=payload.name, email=payload.email,
        password=auth.hash_password(payload.password),
        role=payload.role, status="active",
    )
    db.add(user); db.commit(); db.refresh(user)
    return user


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db),
               _owner: models.User = Depends(require_owner)):
    return db.query(models.User).order_by(models.User.id).all()


@router.delete("/users/{user_id}")
def delete_user(user_id: int,
                db: Session = Depends(get_db),
                owner: models.User = Depends(require_owner)):
    if user_id == owner.id:
        raise HTTPException(400, "Cannot delete the currently signed-in account")
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u: raise HTTPException(404, "User not found")
    db.delete(u); db.commit()
    return {"ok": True}


# ---------------- Notifications (Owner audit) ---------------- #

@router.get("/notifications", response_model=list[schemas.NotificationOut])
def list_notifications(limit: int = 50,
                       db: Session = Depends(get_db),
                       _owner: models.User = Depends(require_owner)):
    return db.query(models.Notification) \
        .order_by(models.Notification.id.desc()).limit(limit).all()
