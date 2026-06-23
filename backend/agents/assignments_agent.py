"""
Assignments Agent — v0.5.

I let teachers create assignments for the classes they teach.
Owners can read everything.
Students see their own class assignments via /student/me/assignments.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
import schemas
import uploads
from dependencies import (
    get_db, require_owner, require_teacher, get_current_user,
)

router = APIRouter(prefix="/assignments", tags=["assignments"])


def submission_out(db: Session, sub: models.AssignmentSubmission) -> dict:
    s = db.query(models.Student).filter(models.Student.id == sub.student_id).first()
    a = db.query(models.Assignment).filter(models.Assignment.id == sub.assignment_id).first()
    return {
        "id": sub.id, "assignment_id": sub.assignment_id, "student_id": sub.student_id,
        "student_name": s.name if s else None,
        "assignment_title": a.title if a else None,
        "max_marks": a.max_marks if a else None,
        "text": sub.text, "file_name": sub.file_name, "status": sub.status,
        "marks_obtained": sub.marks_obtained, "feedback": sub.feedback,
        "submitted_at": sub.submitted_at, "graded_at": sub.graded_at,
    }


def upsert_submission(db: Session, assignment: models.Assignment, student: models.Student,
                      text: str | None, file_name: str | None,
                      file_path: str | None) -> models.AssignmentSubmission:
    """Create or update a student's submission. Re-submit allowed until graded.
    Shared so the student submit endpoint is the only writer. Caller commits."""
    existing = db.query(models.AssignmentSubmission).filter(
        models.AssignmentSubmission.assignment_id == assignment.id,
        models.AssignmentSubmission.student_id == student.id,
    ).first()
    if existing:
        if existing.status == "graded":
            raise ValueError("This submission has already been graded.")
        existing.text = text
        if file_name:
            existing.file_name = file_name
            existing.file_path = file_path
        existing.submitted_at = datetime.utcnow()
        return existing
    sub = models.AssignmentSubmission(
        assignment_id=assignment.id, student_id=student.id,
        text=text, file_name=file_name, file_path=file_path, status="submitted")
    db.add(sub)
    return sub


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


# ---------------- submissions + grading (teacher) ---------------- #

def _owned_assignment(db: Session, assignment_id: int, teacher_user: models.User) -> models.Assignment:
    a = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
    t = _teacher_for_user(db, teacher_user.id)
    if a.teacher_id != t.id:
        raise HTTPException(403, "Not your assignment.")
    return a


@router.get("/{assignment_id}/submissions",
            response_model=list[schemas.AssignmentSubmissionOut])
def list_submissions(assignment_id: int,
                     db: Session = Depends(get_db),
                     teacher_user: models.User = Depends(require_teacher)):
    _owned_assignment(db, assignment_id, teacher_user)
    subs = db.query(models.AssignmentSubmission).filter(
        models.AssignmentSubmission.assignment_id == assignment_id
    ).order_by(models.AssignmentSubmission.submitted_at.desc()).all()
    return [submission_out(db, s) for s in subs]


@router.post("/submissions/{submission_id}/grade",
             response_model=schemas.AssignmentSubmissionOut)
def grade_submission(submission_id: int,
                     payload: schemas.SubmissionGradeIn,
                     db: Session = Depends(get_db),
                     teacher_user: models.User = Depends(require_teacher)):
    sub = db.query(models.AssignmentSubmission).filter(
        models.AssignmentSubmission.id == submission_id).first()
    if not sub:
        raise HTTPException(404, "Submission not found")
    a = _owned_assignment(db, sub.assignment_id, teacher_user)
    if payload.marks_obtained < 0 or payload.marks_obtained > (a.max_marks or 0):
        raise HTTPException(400, f"marks must be between 0 and {a.max_marks}")
    sub.marks_obtained = payload.marks_obtained
    sub.feedback = payload.feedback
    sub.status = "graded"
    sub.graded_by = teacher_user.id
    sub.graded_at = datetime.utcnow()
    db.commit(); db.refresh(sub)
    return submission_out(db, sub)


@router.get("/submissions/{submission_id}/file")
def download_submission(submission_id: int,
                        db: Session = Depends(get_db),
                        teacher_user: models.User = Depends(require_teacher)):
    sub = db.query(models.AssignmentSubmission).filter(
        models.AssignmentSubmission.id == submission_id).first()
    if not sub:
        raise HTTPException(404, "Submission not found")
    _owned_assignment(db, sub.assignment_id, teacher_user)
    if not sub.file_path:
        raise HTTPException(404, "No file attached to this submission.")
    return FileResponse(sub.file_path, filename=sub.file_name or "submission")
