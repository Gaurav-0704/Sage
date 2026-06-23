"""
Teachers — owner CRUD on teaching staff plus a round-trip CSV
(import / export / template). The data/teachers.csv file is automatically
re-written every time a teacher is added, edited, or deleted, so the file
on disk always matches what's in the database.

Each teacher is two database rows: a User (login) and a Teacher (profile).
We keep the User columns Owner-controllable here too: name, email,
status, can_do_front_office.
"""

import csv
import io
from datetime import date as Date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session

import auth
import models
import schemas
import excel_io
from csv_sync import sync_teachers, TEACHER_COLS
from dependencies import get_db, require_owner

router = APIRouter(prefix="/teachers", tags=["teachers"])

DEFAULT_TEACHER_PASSWORD = "teacher123"


def upsert_teacher(
    db: Session, fields: dict, default_password: str = DEFAULT_TEACHER_PASSWORD
) -> tuple[str, models.Teacher]:
    """Insert or update a teacher (User + Teacher rows) keyed on employee_id.

    The manual "Add teacher" form and the Excel/CSV import both funnel through
    here, so the two paths can never diverge. Caller commits + syncs.
    Raises ValueError if a new teacher's email is already taken by someone else.
    Returns ("created"|"updated", teacher).
    """
    existing_t = db.query(models.Teacher).filter(
        models.Teacher.employee_id == fields["employee_id"]
    ).first()

    if existing_t:
        u = db.query(models.User).filter(models.User.id == existing_t.user_id).first()
        if u:
            u.name = fields["name"]
            u.email = fields["email"]
            u.can_do_front_office = fields.get("can_do_front_office", False)
            if "status" in fields:
                u.status = fields["status"]
        for k in ("subject", "classes_taught", "qualification", "phone"):
            if k in fields:
                setattr(existing_t, k, fields[k])
        if "joined_date" in fields:
            existing_t.joined_date = fields["joined_date"]
        return "updated", existing_t

    # New teacher — don't clobber an existing email belonging to someone else.
    if db.query(models.User).filter(models.User.email == fields["email"]).first():
        raise ValueError(f"email {fields['email']!r} is already in use")
    user = models.User(
        name=fields["name"], email=fields["email"],
        password=auth.hash_password(default_password),
        role="teacher", status=fields.get("status", "active"),
        can_do_front_office=fields.get("can_do_front_office", False),
    )
    db.add(user)
    db.flush()   # assign user.id without committing, so dry_run can roll back
    t = models.Teacher(
        user_id=user.id,
        employee_id=fields["employee_id"],
        subject=fields.get("subject"),
        classes_taught=fields.get("classes_taught"),
        qualification=fields.get("qualification"),
        phone=fields.get("phone"),
        joined_date=fields.get("joined_date"),
    )
    db.add(t)
    return "created", t


def _join(db: Session, t: models.Teacher) -> dict:
    u = db.query(models.User).filter(models.User.id == t.user_id).first()
    return {
        "id": t.id, "user_id": t.user_id,
        "employee_id": t.employee_id,
        "name": u.name if u else "", "email": u.email if u else "",
        "role": "teacher", "status": u.status if u else "",
        "can_do_front_office": u.can_do_front_office if u else False,
        "subject": t.subject, "classes_taught": t.classes_taught,
        "qualification": t.qualification, "phone": t.phone,
        "joined_date": t.joined_date, "photo_url": t.photo_url,
    }


# ---------------- CRUD ---------------- #

@router.get("", response_model=list[schemas.TeacherOut])
def list_teachers(db: Session = Depends(get_db),
                  _owner: models.User = Depends(require_owner)):
    rows = db.query(models.Teacher).order_by(models.Teacher.id).all()
    return [_join(db, t) for t in rows]


@router.post("", response_model=schemas.TeacherOut)
def create_teacher(payload: schemas.TeacherCreate,
                   db: Session = Depends(get_db),
                   _owner: models.User = Depends(require_owner)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(400, "Email already in use")
    if db.query(models.Teacher).filter(
        models.Teacher.employee_id == payload.employee_id).first():
        raise HTTPException(400, "Employee id already in use")
    # Same upsert path the Excel/CSV import uses — one source of truth.
    fields = {
        "employee_id":   payload.employee_id,
        "name":          payload.name,
        "email":         payload.email,
        "subject":       payload.subject,
        "classes_taught": payload.classes_taught,
        "qualification": payload.qualification,
        "phone":         payload.phone,
        "can_do_front_office": payload.can_do_front_office,
    }
    try:
        _, t = upsert_teacher(db, fields, default_password=payload.password)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit(); db.refresh(t)
    sync_teachers(db)
    return _join(db, t)


@router.put("/{teacher_id}", response_model=schemas.TeacherOut)
def update_teacher(teacher_id: int,
                   payload: schemas.TeacherUpdate,
                   db: Session = Depends(get_db),
                   _owner: models.User = Depends(require_owner)):
    t = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if not t: raise HTTPException(404, "Teacher not found")
    u = db.query(models.User).filter(models.User.id == t.user_id).first()

    data = payload.model_dump(exclude_unset=True)
    for k in ("subject", "classes_taught", "qualification", "phone"):
        if k in data:
            setattr(t, k, data[k])
    if "can_do_front_office" in data and u:
        u.can_do_front_office = bool(data["can_do_front_office"])
    if "status" in data and u:
        if data["status"] not in ("active", "disabled"):
            raise HTTPException(400, "status must be active|disabled")
        u.status = data["status"]
    db.commit(); db.refresh(t)
    sync_teachers(db)
    return _join(db, t)


@router.delete("/{teacher_id}")
def delete_teacher(teacher_id: int,
                   db: Session = Depends(get_db),
                   _owner: models.User = Depends(require_owner)):
    t = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if not t: raise HTTPException(404, "Teacher not found")
    u = db.query(models.User).filter(models.User.id == t.user_id).first()
    db.delete(t)
    if u: db.delete(u)
    db.commit()
    sync_teachers(db)
    return {"ok": True}


# ---------------- CSV import / export ---------------- #

def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in ("1", "yes", "true", "y", "t")


def _row_to_teacher_fields(row: dict) -> dict:
    """Normalize one CSV row into Teacher kwargs. Raises ValueError on bad data."""
    row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
    if not row.get("employee_id"):
        raise ValueError("employee_id is required")
    if not row.get("name"):
        raise ValueError("name is required")
    if not row.get("email"):
        raise ValueError("email is required")
    fields = {
        "employee_id":   row["employee_id"],
        "name":          row["name"],
        "email":         row["email"],
        "subject":       row.get("subject") or None,
        "classes_taught": row.get("classes_taught") or None,
        "qualification": row.get("qualification") or None,
        "phone":         row.get("phone") or None,
        "can_do_front_office": _truthy(row.get("can_do_front_office", "")),
    }
    if row.get("joined_date"):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                fields["joined_date"] = datetime.strptime(row["joined_date"], fmt).date()
                break
            except ValueError:
                continue
    if row.get("status"):
        if row["status"] not in ("active", "disabled"):
            raise ValueError("status must be active|disabled")
        fields["status"] = row["status"]
    return fields


def _teacher_to_row(t: models.Teacher, u: models.User | None) -> dict:
    return {
        "employee_id":   t.employee_id or "",
        "name":          u.name if u else "",
        "email":         u.email if u else "",
        "subject":       t.subject or "",
        "classes_taught": t.classes_taught or "",
        "qualification": t.qualification or "",
        "phone":         t.phone or "",
        "can_do_front_office": "yes" if (u and u.can_do_front_office) else "no",
        "joined_date":   t.joined_date.isoformat() if t.joined_date else "",
        "status":        u.status if u else "active",
    }


_TEACHER_TEMPLATE_ROW = {
    "employee_id":   "SGET013",
    "name":          "Example Teacher",
    "email":         "first.last@sage.school",
    "subject":       "Math",
    "classes_taught": "5,6,7",
    "qualification": "M.Sc, B.Ed",
    "phone":         "9999900000",
    "can_do_front_office": "no",
    "joined_date":   "2024-06-01",
    "status":        "active",
}


def _teacher_rows(db: Session) -> list[dict]:
    teachers = db.query(models.Teacher).all()
    user_ids = [t.user_id for t in teachers if t.user_id]
    users = {u.id: u for u in db.query(models.User)
                                .filter(models.User.id.in_(user_ids)).all()}
    return [_teacher_to_row(t, users.get(t.user_id)) for t in teachers]


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_db),
               _owner: models.User = Depends(require_owner)):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=TEACHER_COLS, extrasaction="ignore")
    w.writeheader()
    for row in _teacher_rows(db):
        w.writerow(row)
    buf.seek(0)
    today = Date.today().isoformat()
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="teachers_{today}.csv"'},
    )


@router.get("/export.xlsx")
def export_xlsx(db: Session = Depends(get_db),
                _owner: models.User = Depends(require_owner)):
    """Download all teachers as an .xlsx — same column layout as the template."""
    data = excel_io.build_xlsx(TEACHER_COLS, _teacher_rows(db), sheet_title="Teachers")
    today = Date.today().isoformat()
    return Response(
        content=data,
        media_type=excel_io.XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="teachers_{today}.xlsx"'},
    )


@router.get("/template.csv")
def csv_template(_owner: models.User = Depends(require_owner)):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=TEACHER_COLS, extrasaction="ignore")
    w.writeheader()
    w.writerow(_TEACHER_TEMPLATE_ROW)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="teachers_template.csv"'},
    )


@router.get("/template.xlsx")
def xlsx_template(_owner: models.User = Depends(require_owner)):
    """Download a blank .xlsx template (correct headers + one sample row)."""
    data = excel_io.build_xlsx(TEACHER_COLS, [_TEACHER_TEMPLATE_ROW], sheet_title="Teachers")
    return Response(
        content=data,
        media_type=excel_io.XLSX_MIME,
        headers={"Content-Disposition": 'attachment; filename="teachers_template.xlsx"'},
    )


def import_teacher_rows(
    db: Session, rows: list[dict], default_password: str = DEFAULT_TEACHER_PASSWORD,
    dry_run: bool = False,
) -> dict:
    """Validate + upsert a batch of raw teacher rows. Shared by .csv and .xlsx.

    Returns the structured summary {created, updated, skipped, errors[]}.
    Duplicate employee_id *within the same file* is skipped (never duplicated).
    """
    created, updated, skipped, errors = 0, 0, 0, []
    seen_keys: set[str] = set()
    for i, row in enumerate(rows, start=2):
        try:
            fields = _row_to_teacher_fields(row)
        except ValueError as e:
            errors.append({"row": i, "error": str(e)})
            continue

        key = fields["employee_id"]
        if key in seen_keys:
            skipped += 1
            errors.append({"row": i, "error": f"duplicate employee_id {key!r} in file — skipped"})
            continue
        seen_keys.add(key)

        try:
            action, _ = upsert_teacher(db, fields, default_password=default_password)
        except ValueError as e:
            skipped += 1
            errors.append({"row": i, "error": str(e)})
            continue
        if action == "created":
            created += 1
        else:
            updated += 1

    if dry_run:
        db.rollback()
    else:
        db.commit()
        sync_teachers(db)

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
    file: UploadFile = File(..., description="Teachers .xlsx or .csv"),
    default_password: str = Query(
        DEFAULT_TEACHER_PASSWORD,
        description="Initial password for any newly-created teacher accounts.",
    ),
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """Bulk import / sync teachers from .xlsx or .csv. Upserts by employee_id."""
    raw = await file.read()
    try:
        rows = excel_io.read_tabular(file.filename, raw)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return import_teacher_rows(db, rows, default_password=default_password, dry_run=dry_run)
