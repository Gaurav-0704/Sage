"""
Assignments Agent — v0.5.

Teachers create assignments for the classes they teach.
Owner can read everything.
Students see assignments for their own class (via /student/me/assignments).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import (
    get_db, require_owner, require_teacher, get_current_user,
)

router = APIRouter(prefix="/assignments", tags=["assignments"])


def _teacher_for_user(db: Session, user_id: int) -> models.Teacher:
    t = db.query(models.Teacher).filter(models.Teacher.user_id == user_id).first()
    if not t: raise HTTPException(403, "No teacher profile for this account.")
    return t


def _enrich(db: Session, a: models.Assignment) -> dict:
    t = db.query(models.Teacher).filter(models.Teacher.id == a.teacher_id).first()
    teacher_name = ""
    if t:
        u = db.query(models.User).filter(models.User.id == t.user_id).first()
        teacher_name = u.name if u else ""
    return {
        "id": a.id, "teacher_id": a.teacher_id, "teacher_name": teacher_name,
        "student_class": a.student_class, "section": a.section,
        "subject": a.subject, "title": a.title,
        "description": a.description, "due_date": a.due_date,
        "max_marks": a.max_marks, "created_at": a.created_at,
    }


@router.get("", response_model=list[schemas.AssignmentOut])
def list_assignments(student_class: str | None = None,
                     db: Session = Depends(get_db),
                     user: models.User = Depends(get_current_user)):
    """Owner: all. Teacher: own assignments. Student: their class."""
    q = db.query(models.Assignment)
    if user.role == "owner":
        pass
    elif user.role == "teacher":
        t = _teacher_for_user(db, user.id)
        q = q.filter(models.Assignment.teacher_id == t.id)
    elif user.role == "student":
        s = db.query(models.Student).filter(models.Student.user_id == user.id).first()
        if not s: return []
        q = q.filter(models.Assignment.student_class == s.student_class)
    else:
        raise HTTPException(403, "Not allowed")

    if student_class:
        q = q.filter(models.Assignment.student_class == student_class)
    rows = q.order_by(models.Assignment.due_date.asc().nullslast(),
                       models.Assignment.id.desc()).all()
    return [_enrich(db, a) for a in rows]


@router.post("", response_model=schemas.AssignmentOut)
def create_assignment(payload: schemas.AssignmentCreate,
                      db: Session = Depends(get_db),
                      teacher_user: models.User = Depends(require_teacher)):
    t = _teacher_for_user(db, teacher_user.id)
    a = models.Assignment(teacher_id=t.id, **payload.model_dump())
    db.add(a); db.commit(); db.refresh(a)
    return _enrich(db, a)


@router.put("/{assignment_id}", response_model=schemas.AssignmentOut)
def update_assignment(assignment_id: int,
                      payload: schemas.AssignmentUpdate,
                      db: Session = Depends(get_db),
                      teacher_user: models.User = Depends(require_teacher)):
    a = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not a: raise HTTPException(404, "Assignment not found")
    t = _teacher_for_user(db, teacher_user.id)
    if a.teacher_id != t.id:
        raise HTTPException(403, "You can only edit your own assignments.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit(); db.refresh(a)
    return _enrich(db, a)


@router.delete("/{assignment_id}")
def delete_assignment(assignment_id: int,
                      db: Session = Depends(get_db),
                      teacher_user: models.User = Depends(require_teacher)):
    a = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not a: raise HTTPException(404, "Assignment not found")
    t = _teacher_for_user(db, teacher_user.id)
    if a.teacher_id != t.id:
        raise HTTPException(403, "You can only delete your own assignments.")
    db.delete(a); db.commit()
    return {"ok": True}
