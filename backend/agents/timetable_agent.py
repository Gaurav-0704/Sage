"""
Timetable Agent — TIER 1b.

Owner builds the weekly timetable (class/section × day × period → subject,
teacher, room). Conflict detection prevents:
  - two subjects in the same (class, section, day, period) slot, and
  - a teacher being double-booked across classes in the same (day, period).

Teachers see their own schedule; students see their class schedule
(/student/me/timetable lives in student_self_agent).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import (
    get_db, require_owner, require_teacher, require_school_member,
)

router = APIRouter(prefix="/timetable", tags=["timetable"])

_DAYS = schemas.TIMETABLE_DAYS


def _teacher_name(db: Session, teacher_id: int | None) -> str | None:
    if not teacher_id:
        return None
    t = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if not t:
        return None
    u = db.query(models.User).filter(models.User.id == t.user_id).first()
    return u.name if u else None


def _out(db: Session, e: models.TimetableEntry) -> schemas.TimetableEntryOut:
    return schemas.TimetableEntryOut(
        id=e.id, student_class=e.student_class, section=e.section,
        day=e.day, period=e.period, subject=e.subject,
        teacher_id=e.teacher_id, teacher_name=_teacher_name(db, e.teacher_id),
        room=e.room, academic_year=e.academic_year,
    )


def find_conflicts(
    db: Session, *, student_class: str, section: str, day: str, period: int,
    teacher_id: int | None, exclude_id: int | None = None,
) -> list[str]:
    """Return human-readable conflict messages for a proposed slot (empty = ok)."""
    conflicts: list[str] = []

    slot_q = db.query(models.TimetableEntry).filter(
        models.TimetableEntry.student_class == student_class,
        models.TimetableEntry.section == section,
        models.TimetableEntry.day == day,
        models.TimetableEntry.period == period,
    )
    if exclude_id:
        slot_q = slot_q.filter(models.TimetableEntry.id != exclude_id)
    occupied = slot_q.first()
    if occupied:
        conflicts.append(
            f"{student_class}-{section} {day} P{period} already has "
            f"{occupied.subject}."
        )

    if teacher_id:
        tq = db.query(models.TimetableEntry).filter(
            models.TimetableEntry.teacher_id == teacher_id,
            models.TimetableEntry.day == day,
            models.TimetableEntry.period == period,
        )
        if exclude_id:
            tq = tq.filter(models.TimetableEntry.id != exclude_id)
        clash = tq.first()
        if clash:
            conflicts.append(
                f"Teacher is already booked {day} P{period} for "
                f"{clash.student_class}-{clash.section} ({clash.subject})."
            )
    return conflicts


def _validate(payload_day: str, payload_period: int):
    if payload_day not in _DAYS:
        raise HTTPException(400, f"day must be one of {', '.join(_DAYS)}")
    if payload_period < 1:
        raise HTTPException(400, "period must be >= 1")


# ---------------- owner CRUD ---------------- #

@router.post("", response_model=schemas.TimetableEntryOut)
def create_entry(payload: schemas.TimetableEntryCreate,
                 db: Session = Depends(get_db),
                 _owner: models.User = Depends(require_owner)):
    _validate(payload.day, payload.period)
    conflicts = find_conflicts(
        db, student_class=payload.student_class, section=payload.section,
        day=payload.day, period=payload.period, teacher_id=payload.teacher_id)
    if conflicts:
        raise HTTPException(409, " ".join(conflicts))
    e = models.TimetableEntry(**payload.model_dump())
    db.add(e); db.commit(); db.refresh(e)
    return _out(db, e)


@router.put("/{entry_id}", response_model=schemas.TimetableEntryOut)
def update_entry(entry_id: int, payload: schemas.TimetableEntryUpdate,
                 db: Session = Depends(get_db),
                 _owner: models.User = Depends(require_owner)):
    e = db.query(models.TimetableEntry).filter(models.TimetableEntry.id == entry_id).first()
    if not e:
        raise HTTPException(404, "Entry not found")
    data = payload.model_dump(exclude_unset=True)
    new_day = data.get("day", e.day)
    new_period = data.get("period", e.period)
    new_teacher = data.get("teacher_id", e.teacher_id)
    _validate(new_day, new_period)
    conflicts = find_conflicts(
        db, student_class=e.student_class, section=e.section,
        day=new_day, period=new_period, teacher_id=new_teacher,
        exclude_id=e.id)
    if conflicts:
        raise HTTPException(409, " ".join(conflicts))
    for k, v in data.items():
        setattr(e, k, v)
    db.commit(); db.refresh(e)
    return _out(db, e)


@router.delete("/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db),
                 _owner: models.User = Depends(require_owner)):
    e = db.query(models.TimetableEntry).filter(models.TimetableEntry.id == entry_id).first()
    if not e:
        raise HTTPException(404, "Entry not found")
    db.delete(e); db.commit()
    return {"ok": True}


# ---------------- views ---------------- #

@router.get("", response_model=list[schemas.TimetableEntryOut])
def list_entries(
    student_class: str | None = Query(None),
    section: str | None = Query(None),
    teacher_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_school_member),
):
    q = db.query(models.TimetableEntry)
    if student_class:
        q = q.filter(models.TimetableEntry.student_class == student_class)
    if section:
        q = q.filter(models.TimetableEntry.section == section)
    if teacher_id:
        q = q.filter(models.TimetableEntry.teacher_id == teacher_id)
    rows = q.all()
    order = {d: i for i, d in enumerate(_DAYS)}
    rows.sort(key=lambda e: (order.get(e.day, 9), e.period))
    return [_out(db, e) for e in rows]


@router.get("/teacher/me", response_model=list[schemas.TimetableEntryOut])
def my_schedule(user: models.User = Depends(require_teacher),
                db: Session = Depends(get_db)):
    t = db.query(models.Teacher).filter(models.Teacher.user_id == user.id).first()
    if not t:
        raise HTTPException(403, "No teacher profile for this account.")
    rows = db.query(models.TimetableEntry).filter(
        models.TimetableEntry.teacher_id == t.id).all()
    order = {d: i for i, d in enumerate(_DAYS)}
    rows.sort(key=lambda e: (order.get(e.day, 9), e.period))
    return [_out(db, e) for e in rows]
