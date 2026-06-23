"""
Parents Agent — TIER 1c.

Parents self-sign-up (auth_agent) and *claim* a child via admission_no + a
verification (the student's phone on record). An owner approves the link.
Once approved, the parent portal exposes their child's attendance, marks,
fees, assignments and notices — read-only.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

import models
import schemas
import report_cards
from dependencies import get_db, require_parent, require_owner
from agents import attendance_agent, student_self_agent, students_agent

router = APIRouter(prefix="/parent", tags=["parents"])


def _norm(p: str | None) -> str:
    return "".join(ch for ch in (p or "") if ch.isdigit())


def verify_and_link(db: Session, parent_user_id: int,
                    admission_no: str, phone: str) -> models.ParentLink:
    """Verify a claim and create a pending ParentLink. Caller commits.

    Shared by parent signup (auth_agent) and the /parent/claim endpoint so
    the verification rule lives in exactly one place. Raises ValueError on a
    bad claim.
    """
    student = db.query(models.Student).filter(
        models.Student.admission_no == admission_no.strip()
    ).first()
    if not student:
        raise ValueError("No student found with that admission number.")
    # Verify against the phone on the student record (if one is set).
    if student.phone and _norm(student.phone) != _norm(phone):
        raise ValueError("Verification failed — phone does not match our records.")
    existing = db.query(models.ParentLink).filter(
        models.ParentLink.parent_user_id == parent_user_id,
        models.ParentLink.student_id == student.id,
    ).first()
    if existing:
        raise ValueError("You have already claimed this child.")
    link = models.ParentLink(
        parent_user_id=parent_user_id, student_id=student.id, status="pending")
    db.add(link)
    return link


def _approved_student_ids(db: Session, parent_user_id: int) -> list[int]:
    return [l.student_id for l in db.query(models.ParentLink).filter(
        models.ParentLink.parent_user_id == parent_user_id,
        models.ParentLink.status == "approved",
    ).all()]


def _require_child(db: Session, parent_user_id: int, student_id: int) -> models.Student:
    if student_id not in _approved_student_ids(db, parent_user_id):
        raise HTTPException(403, "Not an approved child of yours.")
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s:
        raise HTTPException(404, "Student not found")
    return s


# ---------------- parent: claim + children ---------------- #

@router.post("/claim")
def claim_child(payload: schemas.ParentClaimIn,
                user: models.User = Depends(require_parent),
                db: Session = Depends(get_db)):
    try:
        link = verify_and_link(db, user.id, payload.admission_no, payload.phone)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"ok": True, "status": link.status,
            "message": "Claim submitted — awaiting owner approval."}


@router.get("/me/children", response_model=list[schemas.ParentChildOut])
def my_children(user: models.User = Depends(require_parent),
                db: Session = Depends(get_db)):
    links = db.query(models.ParentLink).filter(
        models.ParentLink.parent_user_id == user.id).all()
    out = []
    for l in links:
        s = db.query(models.Student).filter(models.Student.id == l.student_id).first()
        if not s:
            continue
        out.append(schemas.ParentChildOut(
            student_id=s.id, admission_no=s.admission_no, name=s.name,
            student_class=s.student_class, section=s.section,
            link_status=l.status,
        ))
    return out


@router.get("/me/dashboard")
def dashboard(user: models.User = Depends(require_parent),
              db: Session = Depends(get_db)):
    """One summary card per approved child."""
    children = []
    for sid in _approved_student_ids(db, user.id):
        s = db.query(models.Student).filter(models.Student.id == sid).first()
        if not s:
            continue
        att = attendance_agent.summarize(db, [s.id]).get(s.id, {})
        fees = students_agent._summary_for(s)
        reports = student_self_agent._exam_reports(db, s.id)
        upcoming = db.query(models.Assignment).filter(
            models.Assignment.student_class == s.student_class,
        ).filter(
            (models.Assignment.due_date == None) | (models.Assignment.due_date >= date.today())
        ).count()
        children.append({
            "student_id": s.id, "name": s.name,
            "student_class": s.student_class, "section": s.section,
            "attendance_percentage": att.get("percentage", 0.0),
            "fees_due": fees["due_amount"],
            "recent_marks": [r.model_dump() for r in reports[-2:]],
            "upcoming_assignments": upcoming,
        })
    return {"children": children}


@router.get("/me/children/{student_id}/attendance",
            response_model=schemas.StudentAttendanceOut)
def child_attendance(student_id: int,
                     user: models.User = Depends(require_parent),
                     db: Session = Depends(get_db)):
    s = _require_child(db, user.id, student_id)
    tally = attendance_agent.summarize(db, [s.id]).get(s.id, {
        "total": 0, "present": 0, "absent": 0, "late": 0, "leave": 0, "percentage": 0.0,
    })
    records = db.query(models.Attendance).filter(
        models.Attendance.student_id == s.id
    ).order_by(models.Attendance.date.desc(), models.Attendance.period).limit(60).all()
    return schemas.StudentAttendanceOut(
        **tally, records=[schemas.AttendanceOut.model_validate(r) for r in records])


@router.get("/me/children/{student_id}/marks",
            response_model=list[schemas.StudentExamReport])
def child_marks(student_id: int,
                user: models.User = Depends(require_parent),
                db: Session = Depends(get_db)):
    s = _require_child(db, user.id, student_id)
    return student_self_agent._exam_reports(db, s.id)


@router.get("/me/children/{student_id}/fees")
def child_fees(student_id: int,
               user: models.User = Depends(require_parent),
               db: Session = Depends(get_db)):
    s = _require_child(db, user.id, student_id)
    summary = students_agent._summary_for(s)
    return {
        "student_id": s.id, "name": s.name, **summary,
        "payments": [schemas.PaymentOut.model_validate(p).model_dump() for p in s.payments],
    }


@router.get("/me/children/{student_id}/report-card/{exam_id}")
def child_report_card(student_id: int, exam_id: int,
                      user: models.User = Depends(require_parent),
                      db: Session = Depends(get_db)):
    s = _require_child(db, user.id, student_id)
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    pdf = report_cards.build_report_card(db, s, exam)
    fname = f"report_{s.admission_no}_{exam.name}.pdf".replace(" ", "_")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/me/children/{student_id}/assignments",
            response_model=list[schemas.AssignmentOut])
def child_assignments(student_id: int,
                      user: models.User = Depends(require_parent),
                      db: Session = Depends(get_db)):
    s = _require_child(db, user.id, student_id)
    rows = db.query(models.Assignment).filter(
        models.Assignment.student_class == s.student_class
    ).order_by(models.Assignment.due_date.asc().nullslast()).all()
    return rows


# ---------------- owner: approve parent links ---------------- #

def _enrich_link(db: Session, l: models.ParentLink) -> schemas.ParentLinkOut:
    p = db.query(models.User).filter(models.User.id == l.parent_user_id).first()
    s = db.query(models.Student).filter(models.Student.id == l.student_id).first()
    return schemas.ParentLinkOut(
        id=l.id, parent_user_id=l.parent_user_id, student_id=l.student_id,
        status=l.status,
        parent_name=p.name if p else None, parent_email=p.email if p else None,
        student_name=s.name if s else None, admission_no=s.admission_no if s else None,
    )


@router.get("/links", response_model=list[schemas.ParentLinkOut])
def list_links(status: str | None = None,
               db: Session = Depends(get_db),
               _owner: models.User = Depends(require_owner)):
    q = db.query(models.ParentLink)
    if status:
        q = q.filter(models.ParentLink.status == status)
    return [_enrich_link(db, l) for l in q.order_by(models.ParentLink.id.desc()).all()]


@router.post("/links/{link_id}/approve", response_model=schemas.ParentLinkOut)
def approve_link(link_id: int,
                 db: Session = Depends(get_db),
                 _owner: models.User = Depends(require_owner)):
    l = db.query(models.ParentLink).filter(models.ParentLink.id == link_id).first()
    if not l:
        raise HTTPException(404, "Link not found")
    l.status = "approved"
    db.commit(); db.refresh(l)
    return _enrich_link(db, l)


@router.post("/links/{link_id}/reject", response_model=schemas.ParentLinkOut)
def reject_link(link_id: int,
                db: Session = Depends(get_db),
                _owner: models.User = Depends(require_owner)):
    l = db.query(models.ParentLink).filter(models.ParentLink.id == link_id).first()
    if not l:
        raise HTTPException(404, "Link not found")
    l.status = "rejected"
    db.commit(); db.refresh(l)
    return _enrich_link(db, l)
