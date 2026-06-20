"""
Keeps the data/*.csv source files in step with the database.

Whenever a student or teacher row is created, updated or deleted,
call `sync_students(db)` / `sync_teachers(db)` and the file is rewritten
from scratch. The CSVs always reflect "what the database says now", so
the user can pop the file open in Excel any time and trust it.

Failures are logged but never raised — a sync hiccup must not break the
underlying write the user just made.
"""

import csv
import sys
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

import models
from school_constants import (
    STUDENTS_CSV, TEACHERS_CSV, RECORDS_CSV, DATA_DIR, class_sort_key,
)

STUDENT_COLS = [
    "admission_no", "name", "student_class", "section",
    "aadhaar", "dob", "gender", "parent_name", "phone",
    "address", "last_year_dues", "status", "admission_date",
]

TEACHER_COLS = [
    "employee_id", "name", "email", "subject", "classes_taught",
    "qualification", "phone", "can_do_front_office",
    "joined_date", "status",
]


def _ensure_dir():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[csv_sync] could not create data dir: {e}", file=sys.stderr)


def sync_students(db: Session) -> bool:
    """Rewrite data/seed_students.csv to mirror current DB state."""
    try:
        _ensure_dir()
        rows = db.query(models.Student).all()
        rows.sort(key=lambda s: (class_sort_key(s.student_class),
                                  s.section or "", s.name or ""))
        with open(STUDENTS_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=STUDENT_COLS, extrasaction="ignore")
            w.writeheader()
            for s in rows:
                w.writerow({
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
                })
        return True
    except Exception as e:
        print(f"[csv_sync] students sync failed: {e}", file=sys.stderr)
        return False


RECORD_COLS = [
    "admission_no", "name", "student_class", "section",
    "parent_name", "phone", "address",
    "aadhaar", "dob", "gender",
    "admission_date", "status",
    "total_billed", "total_paid", "outstanding",
    "last_updated",
]


def sync_records(db: Session) -> bool:
    """Rewrite data/students_master.csv — the registrar's archive.

    Includes every student row in the database (active, inactive,
    alumni). For each row we attach computed totals so the file is
    useful as a standalone snapshot.
    """
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        rows = db.query(models.Student).all()
        rows.sort(key=lambda s: (class_sort_key(s.student_class),
                                  s.section or "", s.name or ""))
        now = datetime.utcnow().isoformat(timespec="seconds")

        with open(RECORDS_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=RECORD_COLS, extrasaction="ignore")
            w.writeheader()
            for s in rows:
                billed = sum(f.total_fee for f in s.fees) + (s.last_year_dues or 0)
                paid = sum(p.amount for p in s.payments)
                due = max(0.0, billed - paid)
                w.writerow({
                    "admission_no":   s.admission_no or "",
                    "name":           s.name or "",
                    "student_class":  s.student_class or "",
                    "section":        s.section or "",
                    "parent_name":    s.parent_name or "",
                    "phone":          s.phone or "",
                    "address":        (s.address or "").replace("\n", " "),
                    "aadhaar":        s.aadhaar or "",
                    "dob":            s.dob.isoformat() if s.dob else "",
                    "gender":         s.gender or "",
                    "admission_date": s.admission_date.isoformat() if s.admission_date else "",
                    "status":         s.status or "active",
                    "total_billed":   round(billed, 2),
                    "total_paid":     round(paid, 2),
                    "outstanding":    round(due, 2),
                    "last_updated":   now,
                })
        return True
    except Exception as e:
        print(f"[csv_sync] records sync failed: {e}", file=sys.stderr)
        return False


def sync_teachers(db: Session) -> bool:
    """Rewrite data/teachers.csv to mirror current DB state."""
    try:
        _ensure_dir()
        teachers = db.query(models.Teacher).all()
        # Resolve associated user rows in one shot.
        user_ids = [t.user_id for t in teachers if t.user_id]
        users = {u.id: u for u in db.query(models.User)
                                    .filter(models.User.id.in_(user_ids)).all()}
        teachers.sort(key=lambda t: (t.employee_id or ""))
        with open(TEACHERS_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=TEACHER_COLS, extrasaction="ignore")
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
        return True
    except Exception as e:
        print(f"[csv_sync] teachers sync failed: {e}", file=sys.stderr)
        return False
