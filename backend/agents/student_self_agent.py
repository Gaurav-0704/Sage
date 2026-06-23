"""
Student self-view Agent — v0.5.

/student/me endpoints — tailored views for the signed-in student.
"""

from collections import defaultdict
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session

import models
import schemas
import report_cards
import uploads
from dependencies import get_db, require_student

router = APIRouter(prefix="/student", tags=["student_self"])


def _grade(pct: float) -> str:
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    if pct >= 35: return "E"
    return "F"


def _student_for_user(db: Session, user_id: int) -> models.Student:
    s = db.query(models.Student).filter(models.Student.user_id == user_id).first()
    if not s:
        raise HTTPException(403, "No student record linked to this account.")
    return s


def _exam_reports(db: Session, student_id: int) -> list[schemas.StudentExamReport]:
    marks = db.query(models.Mark).filter(models.Mark.student_id == student_id).all()
    by_exam = defaultdict(list)
    for m in marks: by_exam[m.exam_id].append(m)

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
    out.sort(key=lambda r: (r.date or date.min, r.exam_name))
    return out


@router.get("/me/dashboard", response_model=schemas.StudentDashboardOut)
def dashboard(user: models.User = Depends(require_student),
              db: Session = Depends(get_db)):
    s = _student_for_user(db, user.id)

    assignments = db.query(models.Assignment).filter(
        models.Assignment.student_class == s.student_class
    ).order_by(models.Assignment.due_date.asc().nullslast()).all()
    upcoming = [a for a in assignments
                if not a.due_date or a.due_date >= date.today()][:5]
    enriched = [{
        "id": a.id, "teacher_id": a.teacher_id, "teacher_name": None,
        "student_class": a.student_class, "section": a.section,
        "subject": a.subject, "title": a.title,
        "description": a.description, "due_date": a.due_date,
        "max_marks": a.max_marks, "created_at": a.created_at,
    } for a in upcoming]

    reports = _exam_reports(db, s.id)
    recent = reports[-2:] if reports else []

    next_exam = db.query(models.Exam).filter(
        models.Exam.student_class == s.student_class,
        models.Exam.date != None,
        models.Exam.date >= date.today(),
    ).order_by(models.Exam.date.asc()).first()

    return schemas.StudentDashboardOut(
        name=s.name, student_class=s.student_class, section=s.section,
        upcoming_assignments=enriched,
        recent_marks=recent,
        next_exam=schemas.ExamOut.model_validate(next_exam) if next_exam else None,
    )


@router.get("/me/profile", response_model=schemas.StudentProfileOut)
def profile(user: models.User = Depends(require_student),
            db: Session = Depends(get_db)):
    return _student_for_user(db, user.id)


@router.get("/me/assignments", response_model=list[schemas.AssignmentOut])
def assignments(user: models.User = Depends(require_student),
                db: Session = Depends(get_db)):
    s = _student_for_user(db, user.id)
    rows = db.query(models.Assignment).filter(
        models.Assignment.student_class == s.student_class
    ).order_by(models.Assignment.due_date.asc().nullslast()).all()
    out = []
    for a in rows:
        t = db.query(models.Teacher).filter(models.Teacher.id == a.teacher_id).first()
        teacher_name = ""
        if t:
            u = db.query(models.User).filter(models.User.id == t.user_id).first()
            teacher_name = u.name if u else ""
        out.append({
            "id": a.id, "teacher_id": a.teacher_id, "teacher_name": teacher_name,
            "student_class": a.student_class, "section": a.section,
            "subject": a.subject, "title": a.title,
            "description": a.description, "due_date": a.due_date,
            "max_marks": a.max_marks, "created_at": a.created_at,
        })
    return out


@router.post("/me/assignments/{assignment_id}/submit",
             response_model=schemas.AssignmentSubmissionOut)
async def submit_assignment(assignment_id: int,
                            text: str | None = Form(None),
                            file: UploadFile | None = File(None),
                            user: models.User = Depends(require_student),
                            db: Session = Depends(get_db)):
    """Submit (or re-submit until graded) an assignment for the signed-in student."""
    from agents import assignments_agent
    s = _student_for_user(db, user.id)
    a = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
    if a.student_class != s.student_class:
        raise HTTPException(403, "This assignment is not for your class.")

    file_name = file_path = None
    if file is not None:
        raw = await file.read()
        if raw:
            try:
                file_name, file_path = uploads.save_bytes(file.filename, raw)
            except ValueError as e:
                raise HTTPException(400, str(e))
    if not text and not file_name:
        raise HTTPException(400, "Provide text and/or a file to submit.")
    try:
        sub = assignments_agent.upsert_submission(db, a, s, text, file_name, file_path)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit(); db.refresh(sub)
    return assignments_agent.submission_out(db, sub)


@router.get("/me/submissions", response_model=list[schemas.AssignmentSubmissionOut])
def my_submissions(user: models.User = Depends(require_student),
                   db: Session = Depends(get_db)):
    from agents import assignments_agent
    s = _student_for_user(db, user.id)
    subs = db.query(models.AssignmentSubmission).filter(
        models.AssignmentSubmission.student_id == s.id).all()
    return [assignments_agent.submission_out(db, sub) for sub in subs]


@router.get("/me/submissions/{submission_id}/file")
def download_my_submission(submission_id: int,
                           user: models.User = Depends(require_student),
                           db: Session = Depends(get_db)):
    s = _student_for_user(db, user.id)
    sub = db.query(models.AssignmentSubmission).filter(
        models.AssignmentSubmission.id == submission_id,
        models.AssignmentSubmission.student_id == s.id).first()
    if not sub or not sub.file_path:
        raise HTTPException(404, "File not found")
    return FileResponse(sub.file_path, filename=sub.file_name or "submission")


@router.get("/me/marks", response_model=list[schemas.StudentExamReport])
def marks(user: models.User = Depends(require_student),
          db: Session = Depends(get_db)):
    s = _student_for_user(db, user.id)
    return _exam_reports(db, s.id)


@router.get("/me/performance", response_model=schemas.StudentPerformance)
def performance(user: models.User = Depends(require_student),
                db: Session = Depends(get_db)):
    """Same shape as /students/{id}/performance, scoped to the signed-in student."""
    s = _student_for_user(db, user.id)
    latest = db.query(models.Exam).join(
        models.Mark, models.Mark.exam_id == models.Exam.id
    ).filter(
        models.Mark.student_id == s.id,
        models.Exam.student_class == s.student_class,
    ).order_by(models.Exam.date.desc(), models.Exam.id.desc()).first()

    if not latest:
        return schemas.StudentPerformance(
            student_id=s.id, exam_id=None, exam_name=None,
            student_percentage=None, class_average=None,
            rank=None, class_size=None, subject_breakdown=[],
        )

    marks = db.query(models.Mark).filter(models.Mark.exam_id == latest.id).all()
    totals = defaultdict(lambda: {"obt": 0.0, "mx": 0.0})
    for m in marks:
        totals[m.student_id]["obt"] += m.marks_obtained
        totals[m.student_id]["mx"]  += m.max_marks
    pcts = {sid: (t["obt"] / t["mx"] * 100) if t["mx"] else 0
            for sid, t in totals.items()}
    student_pct = pcts.get(s.id)
    class_avg = sum(pcts.values()) / len(pcts) if pcts else 0
    ranked = sorted(pcts.items(), key=lambda kv: kv[1], reverse=True)
    rank = next((i + 1 for i, (sid, _) in enumerate(ranked) if sid == s.id), None)

    by_subject = defaultdict(list)
    for m in marks:
        pct = (m.marks_obtained / m.max_marks * 100) if m.max_marks else 0
        by_subject[m.subject].append((m.student_id, pct))
    breakdown = []
    for subj, items in by_subject.items():
        avg = sum(p for _, p in items) / len(items) if items else 0
        mine = next((p for sid, p in items if sid == s.id), None)
        breakdown.append({
            "subject": subj,
            "student_percentage": round(mine, 2) if mine is not None else None,
            "class_average": round(avg, 2),
        })
    breakdown.sort(key=lambda r: r["subject"])

    return schemas.StudentPerformance(
        student_id=s.id, exam_id=latest.id, exam_name=latest.name,
        student_percentage=round(student_pct, 2) if student_pct is not None else None,
        class_average=round(class_avg, 2),
        rank=rank, class_size=len(pcts),
        subject_breakdown=breakdown,
    )


@router.get("/me/upcoming-exams", response_model=list[schemas.ExamOut])
def upcoming_exams(user: models.User = Depends(require_student),
                   db: Session = Depends(get_db)):
    s = _student_for_user(db, user.id)
    return db.query(models.Exam).filter(
        models.Exam.student_class == s.student_class,
        models.Exam.date != None,
        models.Exam.date >= date.today(),
    ).order_by(models.Exam.date.asc()).all()


@router.get("/me/timetable", response_model=list[schemas.TimetableEntryOut])
def my_timetable(user: models.User = Depends(require_student),
                 db: Session = Depends(get_db)):
    """The signed-in student's class timetable."""
    from agents import timetable_agent
    s = _student_for_user(db, user.id)
    q = db.query(models.TimetableEntry).filter(
        models.TimetableEntry.student_class == s.student_class)
    if s.section:
        q = q.filter(models.TimetableEntry.section == s.section)
    rows = q.all()
    order = {d: i for i, d in enumerate(schemas.TIMETABLE_DAYS)}
    rows.sort(key=lambda e: (order.get(e.day, 9), e.period))
    return [timetable_agent._out(db, e) for e in rows]


@router.get("/me/report-card/{exam_id}")
def my_report_card(exam_id: int,
                   user: models.User = Depends(require_student),
                   db: Session = Depends(get_db)):
    """The signed-in student's report-card PDF for one exam."""
    s = _student_for_user(db, user.id)
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    pdf = report_cards.build_report_card(db, s, exam)
    fname = f"report_{s.admission_no}_{exam.name}.pdf".replace(" ", "_")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/me/attendance", response_model=schemas.StudentAttendanceOut)
def my_attendance(user: models.User = Depends(require_student),
                  db: Session = Depends(get_db)):
    """The signed-in student's attendance summary + recent records."""
    from agents import attendance_agent
    s = _student_for_user(db, user.id)
    tally = attendance_agent.summarize(db, [s.id]).get(s.id, {
        "total": 0, "present": 0, "absent": 0, "late": 0, "leave": 0, "percentage": 0.0,
    })
    records = db.query(models.Attendance).filter(
        models.Attendance.student_id == s.id
    ).order_by(models.Attendance.date.desc(), models.Attendance.period).limit(60).all()
    return schemas.StudentAttendanceOut(
        **tally, records=[schemas.AttendanceOut.model_validate(r) for r in records],
    )
