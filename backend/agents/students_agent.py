"""
Students Agent — v0.3.

Owner: full CRUD + per-student financial summary.
Staff:  GET /students/roster only — name + class roster, no PII or money info.
"""

import csv
import io
from datetime import date as Date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_

import models
import schemas
import excel_io
from csv_sync import sync_students, sync_records
from dependencies import (
    get_db, require_owner, require_school_member,
)

# Columns we accept in the CSV. admission_no is the natural key.
CSV_COLUMNS = [
    "admission_no", "name", "student_class", "section",
    "aadhaar", "dob", "gender", "parent_name", "phone",
    "address", "last_year_dues", "status", "admission_date",
]

router = APIRouter(prefix="/students", tags=["students"])


def _summary_for(student: models.Student) -> dict:
    """
    The single rule for student-level money math.

        total_fee = (sum of this-year bills) + last-year dues
        paid      = sum of all payments ever made by this student
        due       = max(0, total_fee - paid)         -- never show negative
        credit    = max(0, paid - total_fee)         -- shown when overpaid
    """
    total_fee = sum(f.total_fee for f in student.fees) + (student.last_year_dues or 0)
    paid      = sum(p.amount for p in student.payments)
    due       = max(0.0, total_fee - paid)
    return {"total_fee": float(total_fee), "paid_amount": float(paid),
            "due_amount": float(due)}


# ---------- Staff-safe views ---------- #

@router.get("/roster", response_model=list[schemas.StudentRosterOut])
def roster(
    student_class: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_school_member),
):
    """Active students. Returns only name + class + section (no admission_no)."""
    from school_constants import class_sort_key
    q = db.query(models.Student).filter(models.Student.status == "active")
    if student_class:
        q = q.filter(models.Student.student_class == student_class)
    rows = q.all()
    rows.sort(key=lambda s: (class_sort_key(s.student_class),
                              s.section or "", s.name or ""))
    return rows


@router.get("/by-class", response_model=list[schemas.ClassSummary])
def students_by_class(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_school_member),
):
    """How many active students in each class — sorted KG1, KG2, 1, ..., 10."""
    from sqlalchemy import func
    from school_constants import class_sort_key
    rows = db.query(
        models.Student.student_class, func.count(models.Student.id)
    ).filter(models.Student.status == "active") \
     .group_by(models.Student.student_class).all()
    items = [{"student_class": c, "count": n} for c, n in rows]
    items.sort(key=lambda r: class_sort_key(r["student_class"]))
    return items


@router.get("/{student_id:int}/profile", response_model=schemas.StudentProfileOut)
def student_profile(
    student_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_school_member),
):
    """Safe profile for Staff. No admission_no, no Aadhaar, no fees."""
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s:
        raise HTTPException(404, "Student not found")
    return s


# ---------- Owner-only full views ---------- #

@router.get("", response_model=list[schemas.StudentDetailOut])
def list_students(
    q: str | None = Query(None, description="Search name / admission no / aadhaar"),
    student_class: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    query = db.query(models.Student)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Student.name.ilike(like),
                models.Student.admission_no.ilike(like),
                models.Student.aadhaar.ilike(like),
            )
        )
    if student_class:
        query = query.filter(models.Student.student_class == student_class)
    if status:
        query = query.filter(models.Student.status == status)

    from school_constants import class_sort_key
    students = query.all()
    students.sort(key=lambda s: (class_sort_key(s.student_class),
                                  s.section or "", s.name or ""))
    out = []
    for s in students:
        summary = _summary_for(s)
        out.append(schemas.StudentDetailOut(
            id=s.id, admission_no=s.admission_no, name=s.name,
            aadhaar=s.aadhaar, dob=s.dob, gender=s.gender,
            student_class=s.student_class, section=s.section,
            parent_name=s.parent_name, phone=s.phone,
            address=s.address, photo_url=s.photo_url,
            last_year_dues=s.last_year_dues, status=s.status,
            admission_date=s.admission_date,
            **summary, payments=[],
        ))
    return out


@router.get("/{student_id:int}", response_model=schemas.StudentDetailOut)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    summary = _summary_for(s)
    return schemas.StudentDetailOut(
        id=s.id, admission_no=s.admission_no, name=s.name,
        aadhaar=s.aadhaar, dob=s.dob, gender=s.gender,
        student_class=s.student_class, section=s.section,
        parent_name=s.parent_name, phone=s.phone,
        address=s.address, photo_url=s.photo_url,
        last_year_dues=s.last_year_dues, status=s.status,
        admission_date=s.admission_date,
        **summary,
        payments=[schemas.PaymentOut.model_validate(p) for p in s.payments],
    )


@router.post("", response_model=schemas.StudentOut)
def create_student(
    payload: schemas.StudentCreate,
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    if db.query(models.Student).filter(models.Student.admission_no == payload.admission_no).first():
        raise HTTPException(status_code=400, detail="Admission number already exists")
    # Same upsert path the Excel/CSV import uses — one source of truth.
    _, s = upsert_student(db, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(s)
    sync_students(db)   # keep data/seed_students.csv in step
    sync_records(db)    # keep data/students_master.csv in step
    return s


@router.put("/{student_id:int}", response_model=schemas.StudentOut)
def update_student(
    student_id: int,
    payload: schemas.StudentUpdate,
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    sync_students(db); sync_records(db)
    return s


@router.delete("/{student_id:int}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(s)
    db.commit()
    sync_students(db); sync_records(db)
    return {"ok": True}


# ---------------- CSV import / export ---------------- #

def _parse_date(raw: str) -> Optional[Date]:
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date format: {raw!r} (use YYYY-MM-DD)")


def _row_to_fields(row: dict) -> dict:
    """Normalize one CSV row into Student kwargs. Raises ValueError on bad data."""
    # Lower-case header keys so 'Name' and 'name' both work.
    row = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }

    if not row.get("admission_no"):
        raise ValueError("admission_no is required")
    if not row.get("name"):
        raise ValueError("name is required")
    if not row.get("student_class"):
        raise ValueError("student_class is required")

    fields = {
        "admission_no":  row["admission_no"],
        "name":          row["name"],
        "student_class": row["student_class"],
    }
    # Optional simple strings
    for k in ("section", "aadhaar", "gender", "parent_name", "phone", "address"):
        v = row.get(k)
        if v:
            fields[k] = v

    # Optional numeric
    if row.get("last_year_dues"):
        try:
            fields["last_year_dues"] = float(row["last_year_dues"])
        except ValueError:
            raise ValueError(f"last_year_dues must be a number, got {row['last_year_dues']!r}")

    # Optional dates
    if row.get("dob"):
        fields["dob"] = _parse_date(row["dob"])
    if row.get("admission_date"):
        fields["admission_date"] = _parse_date(row["admission_date"])

    # Optional status
    if row.get("status"):
        if row["status"] not in ("active", "inactive", "alumni"):
            raise ValueError("status must be active|inactive|alumni")
        fields["status"] = row["status"]

    return fields


# ---------- Single source of truth: one upsert path for manual + import ---------- #

def upsert_student(db: Session, fields: dict) -> tuple[str, models.Student]:
    """Insert or update a student keyed on admission_no.

    Both the manual "Add student" form and the Excel/CSV import funnel through
    here so the two paths can never diverge. Caller commits + syncs.
    Returns ("created"|"updated", student).
    """
    existing = db.query(models.Student).filter(
        models.Student.admission_no == fields["admission_no"]
    ).first()
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        return "updated", existing
    s = models.Student(**fields)
    db.add(s)
    return "created", s


def _student_to_row(s: models.Student) -> dict:
    """Flatten a Student into the canonical column layout (export + template share this)."""
    return {
        "admission_no":   s.admission_no or "",
        "name":           s.name or "",
        "student_class":  s.student_class or "",
        "section":        s.section or "",
        "aadhaar":        s.aadhaar or "",
        "dob":            s.dob.isoformat() if s.dob else "",
        "gender":         s.gender or "",
        "parent_name":    s.parent_name or "",
        "phone":          s.phone or "",
        "address":        (s.address or "").replace("\n", " "),
        "last_year_dues": s.last_year_dues or 0,
        "status":         s.status or "active",
        "admission_date": s.admission_date.isoformat() if s.admission_date else "",
    }


_TEMPLATE_ROW = {
    "admission_no":   "A001",
    "name":           "Example Student",
    "student_class":  "5",
    "section":        "A",
    "aadhaar":        "123412341234",
    "dob":            "2015-04-12",
    "gender":         "M",
    "parent_name":    "Parent Name",
    "phone":          "9999900000",
    "address":        "Street, City",
    "last_year_dues": 0,
    "status":         "active",
    "admission_date": "2024-06-01",
}


def _all_students_ordered(db: Session) -> list[models.Student]:
    return db.query(models.Student).order_by(
        models.Student.student_class, models.Student.section, models.Student.name
    ).all()


@router.get("/export.csv")
def export_csv(
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """Download all students as a CSV file."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for s in _all_students_ordered(db):
        writer.writerow(_student_to_row(s))
    buf.seek(0)
    today = Date.today().isoformat()
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="students_{today}.csv"'},
    )


@router.get("/export.xlsx")
def export_xlsx(
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """Download all students as an .xlsx — same column layout as the template."""
    rows = [_student_to_row(s) for s in _all_students_ordered(db)]
    data = excel_io.build_xlsx(CSV_COLUMNS, rows, sheet_title="Students")
    today = Date.today().isoformat()
    return Response(
        content=data,
        media_type=excel_io.XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="students_{today}.xlsx"'},
    )


@router.get("/template.csv")
def csv_template(_owner: models.User = Depends(require_owner)):
    """Download a blank CSV template with one example row."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerow(_TEMPLATE_ROW)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="students_template.csv"'},
    )


@router.get("/template.xlsx")
def xlsx_template(_owner: models.User = Depends(require_owner)):
    """Download a blank .xlsx template (correct headers + one sample row)."""
    data = excel_io.build_xlsx(CSV_COLUMNS, [_TEMPLATE_ROW], sheet_title="Students")
    return Response(
        content=data,
        media_type=excel_io.XLSX_MIME,
        headers={"Content-Disposition": 'attachment; filename="students_template.xlsx"'},
    )


def import_student_rows(db: Session, rows: list[dict], dry_run: bool = False) -> dict:
    """Validate + upsert a batch of raw student rows. Shared by .csv and .xlsx.

    Returns the structured summary {created, updated, skipped, errors[]}.
    Duplicate admission_no *within the same file* is skipped (never duplicated).
    """
    created, updated, skipped, errors = 0, 0, 0, []
    seen_keys: set[str] = set()
    for i, row in enumerate(rows, start=2):  # row 1 is the header
        try:
            fields = _row_to_fields(row)
        except ValueError as e:
            errors.append({"row": i, "error": str(e)})
            continue

        key = fields["admission_no"]
        if key in seen_keys:
            skipped += 1
            errors.append({"row": i, "error": f"duplicate admission_no {key!r} in file — skipped"})
            continue
        seen_keys.add(key)

        action, _ = upsert_student(db, fields)
        if action == "created":
            created += 1
        else:
            updated += 1

    if dry_run:
        db.rollback()
    else:
        db.commit()
        sync_students(db); sync_records(db)   # both CSVs reflect merged state

    return {
        "ok": True,
        "dry_run": dry_run,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "error_count": len(errors),
    }


@router.post("/import")
async def import_records(
    file: UploadFile = File(..., description=".xlsx or .csv with student records"),
    dry_run: bool = Query(False, description="Validate only — do not write to DB"),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """Bulk import / sync students from .xlsx or .csv. Upserts by admission_no."""
    raw = await file.read()
    try:
        rows = excel_io.read_tabular(file.filename, raw)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return import_student_rows(db, rows, dry_run=dry_run)
