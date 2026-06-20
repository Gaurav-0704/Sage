"""
Teacher self-view Agent — v0.5.

/teacher/me endpoints — tailored views for the signed-in teacher.
"""

from collections import defaultdict
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_db, require_teacher

router = APIRouter(prefix="/teacher", tags=["teacher_self"])


def _teacher_for_user(db: Session, user_id: int) -> models.Teacher:
    t = db.query(models.Teacher).filter(models.Teacher.user_id == user_id).first()
    if not t: raise HTTPException(403, "No teacher profile for this account.")
    return t


def _classes_list(t: models.Teacher) -> list[str]:
    if not t.classes_taught: return []
    return [c.strip() for c in t.classes_taught.split(",") if c.strip()]


@router.get("/me/dashboard", response_model=schemas.TeacherDashboardOut)
def dashboard(user: models.User = Depends(require_teacher),
              db: Session = Depends(get_db)):
    t = _teacher_for_user(db, user.id)
    classes = _classes_list(t)

    students_count = 0
    if classes:
        students_count = db.query(models.Student).filter(
            models.Student.student_class.in_(classes),
            models.Student.status == "active",
        ).count()

    assignments = db.query(models.Assignment).filter(
        models.Assignment.teacher_id == t.id
    ).order_by(models.Assignment.due_date.asc().nullslast()).all()
    upcoming = [a for a in assignments if not a.due_date or a.due_date >= date.today()][:5]

    enriched = [{
        "id": a.id, "teacher_id": a.teacher_id, "teacher_name": user.name,
        "student_class": a.student_class, "section": a.section,
        "subject": a.subject, "title": a.title,
        "description": a.description, "due_date": a.due_date,
        "max_marks": a.max_marks, "created_at": a.created_at,
    } for a in upcoming]

    return schemas.TeacherDashboardOut(
        classes=classes, students_count=students_count,
        assignments_count=len(assignments),
        upcoming_due=enriched,
    )


@router.get("/me/classes")
def my_classes(user: models.User = Depends(require_teacher),
               db: Session = Depends(get_db)):
    """My class list with student counts."""
    t = _teacher_for_user(db, user.id)
    classes = _classes_list(t)
    out = []
    for c in classes:
        n = db.query(models.Student).filter(
            models.Student.student_class == c,
            models.Student.status == "active",
        ).count()
        out.append({"student_class": c, "count": n})
    return out


@router.get("/me/students/{student_class}", response_model=list[schemas.StudentRosterOut])
def students_in_class(student_class: str,
                      user: models.User = Depends(require_teacher),
                      db: Session = Depends(get_db)):
    t = _teacher_for_user(db, user.id)
    if student_class not in _classes_list(t):
        raise HTTPException(403, "You don't teach this class.")
    return db.query(models.Student).filter(
        models.Student.student_class == student_class,
        models.Student.status == "active",
    ).order_by(models.Student.section, models.Student.name).all()
