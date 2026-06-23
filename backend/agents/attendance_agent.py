"""
Attendance Agent — TIER 1a.

Daily (period 0) and period-wise student attendance.
  - Teachers mark attendance for the classes they teach.
  - Owner / staff can mark and view any class.
  - Students see their own via /student/me/attendance (student_self_agent).
  - Parents see their child's via the parent portal (parents_agent).

A (student_id, date, period) slot is unique — re-marking updates it, so the
mark endpoint is a safe upsert and never duplicates.
"""

from collections import defaultdict
from datetime import date as Date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models
import schemas
from school_constants import class_sort_key
from dependencies import (
    get_db, require_attendance_marker, require_owner,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])

_STATUSES = schemas.ATTENDANCE_STATUSES


def _teacher_classes(db: Session, user: models.User) -> list[str]:
    t = db.query(models.Teacher).filter(models.Teacher.user_id == user.id).first()
    if not t or not t.classes_taught:
        return []
    return [c.strip() for c in t.classes_taught.split(",") if c.strip()]


def _guard_class_access(db: Session, user: models.User, student_class: str):
    """Teachers may only touch their own classes; owner/staff are unrestricted."""
    if user.role == "teacher" and student_class not in _teacher_classes(db, user):
        raise HTTPException(403, "You don't teach this class.")


def mark_attendance(
    db: Session, *, student_class: str, section: str | None,
    on_date: Date, period: int, rows: list, marked_by: int | None,
) -> dict:
    """Upsert attendance for a set of students on one date+period slot.

    Shared core so the logic is testable without HTTP. Caller commits.
    Returns {created, updated, errors[]}.
    """
    created, updated, errors = 0, 0, []
    valid_ids = {
        s.id for s in db.query(models.Student.id).filter(
            models.Student.student_class == student_class
        ).all()
    }
    for r in rows:
        sid = r.student_id if hasattr(r, "student_id") else r["student_id"]
        status = r.status if hasattr(r, "status") else r["status"]
        if status not in _STATUSES:
            errors.append({"student_id": sid, "error": f"invalid status {status!r}"})
            continue
        if sid not in valid_ids:
            errors.append({"student_id": sid, "error": "not in this class"})
            continue
        existing = db.query(models.Attendance).filter(
            models.Attendance.student_id == sid,
            models.Attendance.date == on_date,
            models.Attendance.period == period,
        ).first()
        if existing:
            existing.status = status
            existing.marked_by = marked_by
            updated += 1
        else:
            db.add(models.Attendance(
                student_id=sid, date=on_date, period=period,
                status=status, marked_by=marked_by,
            ))
            created += 1
    return {"created": created, "updated": updated,
            "errors": errors, "error_count": len(errors)}


def summarize(db: Session, student_ids: list[int],
              start: Date | None = None, end: Date | None = None) -> dict[int, dict]:
    """Per-student tallies over an optional date window. present+late = attended."""
    q = db.query(models.Attendance).filter(models.Attendance.student_id.in_(student_ids))
    if start:
        q = q.filter(models.Attendance.date >= start)
    if end:
        q = q.filter(models.Attendance.date <= end)
    tally: dict[int, dict] = {
        sid: {"total": 0, "present": 0, "absent": 0, "late": 0, "leave": 0}
        for sid in student_ids
    }
    for a in q.all():
        t = tally.setdefault(
            a.student_id,
            {"total": 0, "present": 0, "absent": 0, "late": 0, "leave": 0},
        )
        t["total"] += 1
        if a.status in t:
            t[a.status] += 1
    for sid, t in tally.items():
        attended = t["present"] + t["late"]
        t["percentage"] = round(attended / t["total"] * 100, 1) if t["total"] else 0.0
    return tally


# ---------------- endpoints ---------------- #

@router.post("/mark")
def mark(
    payload: schemas.AttendanceMarkIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_attendance_marker),
):
    """Mark/update attendance for a class on one date + period."""
    if not payload.rows:
        raise HTTPException(400, "No rows to mark")
    _guard_class_access(db, user, payload.student_class)
    on_date = payload.date or Date.today()
    result = mark_attendance(
        db, student_class=payload.student_class, section=payload.section,
        on_date=on_date, period=payload.period, rows=payload.rows,
        marked_by=user.id,
    )
    db.commit()
    return {"ok": True, "date": on_date.isoformat(),
            "period": payload.period, **result}


@router.get("/class", response_model=list[schemas.AttendanceClassRow])
def class_sheet(
    student_class: str = Query(...),
    section: str | None = Query(None),
    date: Date | None = Query(None),
    period: int = Query(0),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_attendance_marker),
):
    """Roster for a class with each student's status for the given slot (pre-fill)."""
    _guard_class_access(db, user, student_class)
    on_date = date or Date.today()
    q = db.query(models.Student).filter(
        models.Student.student_class == student_class,
        models.Student.status == "active",
    )
    if section:
        q = q.filter(models.Student.section == section)
    students = q.order_by(models.Student.section, models.Student.name).all()

    marked = {
        a.student_id: a.status for a in db.query(models.Attendance).filter(
            models.Attendance.date == on_date,
            models.Attendance.period == period,
            models.Attendance.student_id.in_([s.id for s in students]),
        ).all()
    }
    return [schemas.AttendanceClassRow(
        student_id=s.id, name=s.name, section=s.section,
        status=marked.get(s.id),
    ) for s in students]


@router.get("/summary", response_model=list[schemas.AttendanceSummaryRow])
def class_summary(
    student_class: str = Query(...),
    section: str | None = Query(None),
    start: Date | None = Query(None),
    end: Date | None = Query(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_attendance_marker),
):
    """Attendance % per student in a class over an optional date window."""
    _guard_class_access(db, user, student_class)
    q = db.query(models.Student).filter(
        models.Student.student_class == student_class,
        models.Student.status == "active",
    )
    if section:
        q = q.filter(models.Student.section == section)
    students = q.all()
    students.sort(key=lambda s: (s.section or "", s.name or ""))
    tally = summarize(db, [s.id for s in students], start, end)
    return [schemas.AttendanceSummaryRow(
        student_id=s.id, name=s.name, section=s.section, **tally[s.id],
    ) for s in students]


@router.get("/student/{student_id}", response_model=list[schemas.AttendanceOut])
def student_history(
    student_id: int,
    start: Date | None = Query(None),
    end: Date | None = Query(None),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """Full attendance history for one student (owner view)."""
    q = db.query(models.Attendance).filter(models.Attendance.student_id == student_id)
    if start:
        q = q.filter(models.Attendance.date >= start)
    if end:
        q = q.filter(models.Attendance.date <= end)
    return q.order_by(models.Attendance.date.desc(), models.Attendance.period).all()
