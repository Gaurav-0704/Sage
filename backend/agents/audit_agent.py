"""
Audit Agent — v0.7.

Records every state-changing API request (POST / PUT / DELETE / PATCH) to
the audit_logs table, along with who did it. Owner can browse + filter + search.

Read-side endpoints live here. The actual recording is done by the
AuditMiddleware which is mounted in main.py.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_db, require_owner

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[schemas.AuditLogOut])
def list_logs(
    user_id: int | None = None,
    user_name: str | None = None,
    role: str | None = None,
    method: str | None = None,
    search: str | None = None,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = db.query(models.AuditLog).filter(models.AuditLog.created_at >= cutoff)
    if user_id is not None:
        q = q.filter(models.AuditLog.user_id == user_id)
    if user_name:
        q = q.filter(models.AuditLog.user_name.ilike(f"%{user_name}%"))
    if role:
        q = q.filter(models.AuditLog.user_role == role)
    if method:
        q = q.filter(models.AuditLog.method == method.upper())
    if search:
        like = f"%{search}%"
        q = q.filter(or_(
            models.AuditLog.summary.ilike(like),
            models.AuditLog.path.ilike(like),
            models.AuditLog.user_name.ilike(like),
        ))
    return q.order_by(models.AuditLog.id.desc()).limit(limit).all()


@router.get("/actors")
def list_actors(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """Distinct users who made changes — for the filter dropdown."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = db.query(
        models.AuditLog.user_id,
        models.AuditLog.user_name,
        models.AuditLog.user_role,
    ).filter(
        models.AuditLog.created_at >= cutoff,
        models.AuditLog.user_id != None,
    ).distinct().all()
    seen = set()
    out = []
    for uid, uname, urole in rows:
        if uid not in seen:
            seen.add(uid)
            out.append({"id": uid, "name": uname, "role": urole})
    return out


@router.get("/summary")
def audit_summary(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """Counts of actions per user-role over the window."""
    from sqlalchemy import func
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = db.query(
        models.AuditLog.user_role,
        models.AuditLog.method,
        func.count(models.AuditLog.id),
    ).filter(models.AuditLog.created_at >= cutoff) \
     .group_by(models.AuditLog.user_role, models.AuditLog.method).all()
    out = {}
    for role, method, count in rows:
        out.setdefault(role or "anonymous", {})
        out[role or "anonymous"][method] = count
    return out
