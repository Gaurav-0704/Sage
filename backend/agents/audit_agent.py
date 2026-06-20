"""
Audit Agent — v0.6.

Records every state-changing API request (POST / PUT / DELETE / PATCH) to
the audit_logs table, along with who did it. Owner can browse + filter.

Read-side endpoints live here. The actual recording is done by the
AuditMiddleware which is mounted in main.py.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_db, require_owner

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[schemas.AuditLogOut])
def list_logs(
    user_id: int | None = None,
    role: str | None = None,
    method: str | None = None,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = db.query(models.AuditLog).filter(models.AuditLog.created_at >= cutoff)
    if user_id is not None:
        q = q.filter(models.AuditLog.user_id == user_id)
    if role:
        q = q.filter(models.AuditLog.user_role == role)
    if method:
        q = q.filter(models.AuditLog.method == method.upper())
    return q.order_by(models.AuditLog.id.desc()).limit(limit).all()


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
