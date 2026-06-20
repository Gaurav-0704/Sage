"""
Exams Agent — v0.4.

I give owners full CRUD on exams and bulk marks entry per class.
Staff can read marks and per-student performance.
"""

from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_db, require_owner, require_staff_or_owner

router = APIRouter(tags=["exams"])

DEFAULT_SUBJECTS = ["English", "Hindi", "Math", "Science", "Social"]


def _grade(pct: float) -> str:
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    if pct >= 35: return "E"
    return "F"


# ---------- Exam CRUD ---------- #

@router.get("/exams", response_model=list[schemas.ExamOut])
def list_exams(
    student_class: str | None = None,
    academic_year: str | None = None,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_staff_or_owner),
):
    q = db.query(models.Exam)
    if student_class:
        q = q.filter(models.Exam.student_class == student_class)
    if academic_year:
        q = q.filter(models.Exam.academic_year == academic_year)
    return q.order_by(models.Exam.academic_year.desc(), models.Exam.date.desc(),
                       models.Exam.id.desc()).all()


@router.post("/exams", response_model=schemas.ExamOut)
def create_exam(payload: schemas.ExamCreate,
                db: Session = Depends(get_db),
                _owner: models.User = Depends(require_owner)):
    e = models.Exam(**payload.model_dump())
    db.add(e); db.commit(); db.refresh(e)
    return e


@router.delete("/exams/{exam_id}")
def delete_exam(exam_id: int,
                db: Session = Depends(get_db),
                _owner: models.User = Depends(require_owner)):
    e = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not e: raise HTTPException(404, "Exam not found")
    db.delete(e); db.commit()
    return {"ok": True}


# ---------- Marks (bulk save & read) ---------- #

@router.get("/exams/{exam_id}/marks", response_model=list[schemas.MarkOut])
def list_marks(exam_id: int,
               db: Session = Depends(get_db),
               _user: models.User = Depends(require_staff_or_owner)):
    return db.query(models.Mark).filter(models.Mark.exam_id == exam_id).all()


@router.post("/exams/{exam_id}/marks/bulk")
def save_marks_bulk(exam_id: int,
                    payload: schemas.MarksBulkIn,
                    db: Session = Depends(get_db),
                    _owner: models.User = Depends(require_owner)):
    """Replace any existing marks for these (student, subject) pairs in this exam."""
    if payload.exam_id != exam_id:
        raise HTTPException(400, "exam_id mismatch between URL and body")
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam: raise HTTPException(404, "Exam not found")

    # Index existing rows for fast upsert.
    existing = db.query(models.Mark).filter(models.Mark.exam_id == exam_id).all()
    by_key = {(m.student_id, m.subject.lower()): m for m in existing}

    saved = 0
    for r in payload.rows:
        if r.marks_obtained < 0 or r.marks_obtained > r.max_marks:
            raise HTTPException(400,
                f"marks for student {r.student_id} subject {r.subject!r} out of range "
                f"(0..{r.max_marks})")
        key = (r.student_id, r.subject.lower())
        if key in by_key:
            m = by_key[key]
            m.marks_obtained = r.marks_obtained
            m.max_marks = r.max_marks
        else:
            db.add(models.Mark(
                exam_id=exam_id, student_id=r.student_id,
                subject=r.subject, max_marks=r.max_marks,
                marks_obtained=r.marks_obtained,
            ))
        saved += 1
    db.commit()
    return {"ok": True, "saved": saved}


# ---------- Per-student views ---------- #

@router.get("/students/{student_id}/exam-reports", response_model=list[schemas.StudentExamReport])
def student_reports(student_id: int,
                    db: Session = Depends(get_db),
                    _user: models.User = Depends(require_staff_or_owner)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student: raise HTTPException(404, "Student not found")

    marks = db.query(models.Mark).filter(models.Mark.student_id == student_id).all()
    by_exam = defaultdict(list)
    for m in marks:
        by_exam[m.exam_id].append(m)

    out = []
    for exam_id, ms in by_exam.items():
        exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
        if not exam: continue
        total_obt = sum(m.marks_obtained for m in ms)
        total_max = sum(m.max_marks for m in ms)
        pct = (total_obt / total_max * 100) if total_max else 0
        out.append(schemas.StudentExamReport(
            exam_id=exam.id, exam_name=exam.name,
            academic_year=exam.academic_year, date=exam.date,
            total_obtained=total_obt, total_max=total_max,
            percentage=round(pct, 2), grade=_grade(pct),
            subjects=[schemas.MarkOut.model_validate(m) for m in ms],
        ))
    out.sort(key=lambda r: (r.date or "", r.exam_name))
    return out


@router.get("/students/{student_id}/performance", response_model=schemas.StudentPerformance)
def student_performance(student_id: int,
                        db: Session = Depends(get_db),
                        _user: models.User = Depends(require_staff_or_owner)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student: raise HTTPException(404, "Student not found")

    # Latest exam in this student's class that they have marks for.
    latest = db.query(models.Exam).join(models.Mark, models.Mark.exam_id == models.Exam.id) \
        .filter(models.Mark.student_id == student_id,
                models.Exam.student_class == student.student_class) \
        .order_by(models.Exam.date.desc(), models.Exam.id.desc()).first()

    if not latest:
        return schemas.StudentPerformance(
            student_id=student_id, exam_id=None, exam_name=None,
            student_percentage=None, class_average=None,
            rank=None, class_size=None, subject_breakdown=[],
        )

    # All marks for this exam.
    marks = db.query(models.Mark).filter(models.Mark.exam_id == latest.id).all()

    # Per-student totals.
    totals = defaultdict(lambda: {"obt": 0.0, "mx": 0.0})
    for m in marks:
        totals[m.student_id]["obt"] += m.marks_obtained
        totals[m.student_id]["mx"]  += m.max_marks

    pcts = {sid: (t["obt"] / t["mx"] * 100) if t["mx"] else 0
            for sid, t in totals.items()}

    student_pct = pcts.get(student_id)
    class_avg = sum(pcts.values()) / len(pcts) if pcts else 0
    ranked = sorted(pcts.items(), key=lambda kv: kv[1], reverse=True)
    rank = next((i + 1 for i, (sid, _) in enumerate(ranked) if sid == student_id), None)

    # Subject-wise: this student vs class average for each subject.
    by_subject = defaultdict(list)
    for m in marks:
        pct = (m.marks_obtained / m.max_marks * 100) if m.max_marks else 0
        by_subject[m.subject].append((m.student_id, pct))
    breakdown = []
    for subj, items in by_subject.items():
        avg = sum(p for _, p in items) / len(items) if items else 0
        mine = next((p for sid, p in items if sid == student_id), None)
        breakdown.append({
            "subject": subj,
            "student_percentage": round(mine, 2) if mine is not None else None,
            "class_average": round(avg, 2),
        })
    breakdown.sort(key=lambda r: r["subject"])

    return schemas.StudentPerformance(
        student_id=student_id, exam_id=latest.id, exam_name=latest.name,
        student_percentage=round(student_pct, 2) if student_pct is not None else None,
        class_average=round(class_avg, 2),
        rank=rank, class_size=len(pcts),
        subject_breakdown=breakdown,
    )
