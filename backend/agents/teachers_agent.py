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
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import auth
import models
import schemas
from csv_sync import sync_teachers, TEACHER_COLS
from dependencies import get_db, require_owner

router = APIRouter(prefix="/teachers", tags=["teachers"])


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
    user = models.User(
        name=payload.name, email=payload.email,
        password=auth.hash_password(payload.password),
        role="teacher", status="active",
        can_do_front_office=payload.can_do_front_office,
    )
    db.add(user); db.commit(); db.refresh(user)
    t = models.Teacher(
        user_id=user.id,
        employee_id=payload.employee_id,
        subject=payload.subject,
        classes_taught=payload.classes_taught,
        qualification=payload.qualification,
        phone=payload.phone,
    )
    db.add(t); db.commit(); db.refresh(t)
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


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_db),
               _owner: models.User = Depends(require_owner)):
    teachers = db.query(models.Teacher).all()
    user_ids = [t.user_id for t in teachers if t.user_id]
    users = {u.id: u for u in db.query(models.User)
                                .filter(models.User.id.in_(user_ids)).all()}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=TEACHER_COLS, extrasaction="ignore")
    w.writeheader()
    for t in teachers:
        u = users.get(t.user_id)
        w.writerow({
            "employee_id":   t.employee_id or "",
            "name":          u.name if u else "",
            "email":         u.email if u else "",
            "subject":       t.subject or "",
            "classes_taught": t.classes_taught or "",
            "qualification": t.qualification or "",
            "phone":         t.phone or "",
            "can_do_front_office":
                "yes" if (u and u.can_do_front_office) else "no",
            "joined_date":   t.joined_date.isoformat() if t.joined_date else "",
            "status":        u.status if u else "active",
        })
    buf.seek(0)
    today = Date.today().isoformat()
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="teachers_{today}.csv"'},
    )


@router.get("/template.csv")
def csv_template(_owner: models.User = Depends(require_owner)):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=TEACHER_COLS, extrasaction="ignore")
    w.writeheader()
    w.writerow({
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
    })
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="teachers_template.csv"'},
    )


@router.post("/import")
async def import_csv(
    file: UploadFile = File(..., description="Teachers CSV"),
    default_password: str = Query(
        "teacher123",
        description="Used as the initial password for any newly-created teacher accounts.",
    ),
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """Bulk import / sync teachers. Upserts by employee_id (then email)."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except Exception:
            raise HTTPException(400, "Could not decode file. Save as UTF-8 CSV and retry.")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, "CSV is empty or missing a header row")

    created, updated, errors = 0, 0, []
    for i, row in enumerate(reader, start=2):
        try:
            fields = _row_to_teacher_fields(row)
        except ValueError as e:
            errors.append({"row": i, "error": str(e)})
            continue

        existing_t = db.query(models.Teacher).filter(
            models.Teacher.employee_id == fields["employee_id"]).first()

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
            updated += 1
        else:
            # Don't allow CSV upload to clobber an existing email of a non-teacher.
            if db.query(models.User).filter(models.User.email == fields["email"]).first():
                errors.append({"row": i,
                                "error": f"email {fields['email']!r} is already in use"})
                continue
            user = models.User(
                name=fields["name"], email=fields["email"],
                password=auth.hash_password(default_password),
                role="teacher", status=fields.get("status", "active"),
                can_do_front_office=fields.get("can_do_front_office", False),
            )
            db.add(user); db.commit(); db.refresh(user)
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
            created += 1

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
        "errors": errors,
        "error_count": len(errors),
    }
