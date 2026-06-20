"""
AI Assistant — Owner-only.

The Owner can ask in plain English ("add a student named Riya in class 5",
"who has more than ₹20,000 outstanding?") and the assistant proposes
concrete actions. NOTHING runs until the Owner confirms each action — the
assistant's only job is to plan; the Owner does the committing.

Safety rules baked in:

  * Only Owners can talk to the assistant.
  * The assistant is asked to ask clarifying questions when anything is
    ambiguous instead of guessing.
  * Each proposed action is shown as a separate row that the Owner can
    skip individually before clicking Apply.
  * Destructive actions (delete_*) are flagged extra-bright and require an
    additional in-browser confirm.

Configure with `ANTHROPIC_API_KEY`. Without a key the chat endpoint
returns a clear "not configured" error; everything else still works.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import date as Date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import auth
import models
import schemas
from dependencies import get_db, require_owner

router = APIRouter(prefix="/ai", tags=["ai"])

ANTHROPIC_KEY    = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL  = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_URL    = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = """You are the in-house assistant for Nagarjuna High School's ERP.
You help the Owner make changes by proposing precise, named tool calls.

YOUR RULES — non-negotiable:

1. ASK BEFORE GUESSING. If anything in the request is ambiguous (which
   student? which class? which fee? what amount?) reply with a short
   clarifying question instead of proposing actions. Examples:
     - "I see two students named Riya in class 5. Did you mean Riya Sharma
       (NHS0042) or Riya Patel (NHS0058)?"
     - "Should this payment be cash or bank?"

2. VERIFY FIRST. Before deleting or updating anything, call a list_* /
   get_* tool first to confirm the right row(s). Only then propose the
   change.

3. ONE INTENT, MINIMAL ACTIONS. Use the smallest set of actions that
   completes the request. Don't bundle unrelated changes.

4. EXACT NUMBERS, NEVER ROUND. When the Owner says "increase by 10%",
   compute the actual new value and show it ("₹24,000 → ₹26,400") in your
   reply text.

5. NO HARM. For destructive actions you MUST:
     - explicitly list what will be deleted ("Will delete student NHS0042
       Riya Sharma — this also removes 3 fee bills and 2 payments")
     - propose the action and stop; let the Owner read before they confirm.

6. STAY IN SCOPE. You can only do school operations using the tools
   provided. If asked anything outside (e.g., write a poem), politely
   decline and offer something useful you CAN do.

7. HONEST UNCERTAINTY. If you don't have a tool for what's asked, say so.
   Never invent a tool name.

Today: {today}.  School: Nagarjuna High School (NHS), classes KG1 to 10.
"""


# -----------------------------------------------------------------------
# Tool catalogue. Each entry is what Claude sees; each name maps to a
# Python function `_t_*` below that takes (db, **args).
# -----------------------------------------------------------------------

TOOLS = [
    # ---- Read tools (use these first to verify) ---- #
    {
        "name": "list_students",
        "description": "Find students. Filter by class and/or free-text (matches name + admission no).",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_class": {"type": "string"},
                "search":        {"type": "string"},
                "limit":         {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "get_student",
        "description": "Get one student's full record by id, including fee summary.",
        "input_schema": {
            "type": "object",
            "properties": {"student_id": {"type": "integer"}},
            "required": ["student_id"],
        },
    },
    {
        "name": "list_teachers",
        "description": "List all teachers and their classes/subjects.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_fee_structures",
        "description": "List fee structures, optionally filtered by class and/or year.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_class": {"type": "string"},
                "academic_year": {"type": "string"},
            },
        },
    },
    {
        "name": "list_assignments",
        "description": "List recent assignments. Filter by class.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_class": {"type": "string"},
                "limit":         {"type": "integer", "default": 25},
            },
        },
    },
    {
        "name": "get_dashboard_stats",
        "description": "School-level totals: students, billed, collected, due, expenses, balances.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_top_dues",
        "description": "Students with the highest outstanding dues. Useful for follow-up calls.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit":     {"type": "integer", "default": 10},
                "min_due":   {"type": "number"},
            },
        },
    },
    {
        "name": "list_recent_payments",
        "description": "Most recent payments across all students.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 20}},
        },
    },
    {
        "name": "list_recent_expenses",
        "description": "Most recent expenses across all categories.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 20}},
        },
    },

    # ---- Write tools — Owner reviews each one before it runs ---- #
    {
        "name": "create_student",
        "description": "Create a new student. admission_no, name, student_class are required.",
        "input_schema": {
            "type": "object",
            "properties": {
                "admission_no":   {"type": "string"},
                "name":           {"type": "string"},
                "student_class":  {"type": "string", "description": "KG1, KG2, or 1..10"},
                "section":        {"type": "string"},
                "parent_name":    {"type": "string"},
                "phone":          {"type": "string"},
                "aadhaar":        {"type": "string"},
                "last_year_dues": {"type": "number"},
            },
            "required": ["admission_no", "name", "student_class"],
        },
    },
    {
        "name": "update_student",
        "description": "Update specific fields on a student. Only include fields you want to change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"},
                "fields":     {"type": "object",
                                "description": "Map of field name to new value"},
            },
            "required": ["student_id", "fields"],
        },
    },
    {
        "name": "delete_student",
        "description": "DESTRUCTIVE. Permanently delete a student plus their fees and payments.",
        "input_schema": {
            "type": "object",
            "properties": {"student_id": {"type": "integer"}},
            "required": ["student_id"],
        },
    },
    {
        "name": "set_student_status",
        "description": "Set student status to 'active', 'inactive', or 'alumni'. Non-destructive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"},
                "status":     {"type": "string", "enum": ["active", "inactive", "alumni"]},
            },
            "required": ["student_id", "status"],
        },
    },
    {
        "name": "create_fee_structure",
        "description": "Define the per-class fee for an academic year. Doesn't bill students yet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_class":  {"type": "string"},
                "academic_year":  {"type": "string", "description": "e.g. 2025-26"},
                "tuition_fee":    {"type": "number", "default": 0},
                "transport_fee":  {"type": "number", "default": 0},
                "books_fee":      {"type": "number", "default": 0},
                "uniform_fee":    {"type": "number", "default": 0},
                "other_fee":      {"type": "number", "default": 0},
            },
            "required": ["student_class", "academic_year"],
        },
    },
    {
        "name": "update_fee_structure",
        "description": "Change one or more fee fields on an existing structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "structure_id": {"type": "integer"},
                "fields":       {"type": "object"},
            },
            "required": ["structure_id", "fields"],
        },
    },
    {
        "name": "apply_fee_structure",
        "description": "Generate fee bills for every active student in this structure's class. Skips students who already have a bill for that year.",
        "input_schema": {
            "type": "object",
            "properties": {"structure_id": {"type": "integer"}},
            "required": ["structure_id"],
        },
    },
    {
        "name": "record_payment",
        "description": "Record a fee payment. Auto-applied to oldest outstanding bill.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"},
                "amount":     {"type": "number"},
                "mode":       {"type": "string", "enum": ["cash", "bank"]},
                "fee_head":   {"type": "string"},
                "note":       {"type": "string"},
            },
            "required": ["student_id", "amount", "mode"],
        },
    },
    {
        "name": "record_expense",
        "description": "Record a school expense.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":     {"type": "string"},
                "amount":    {"type": "number"},
                "category":  {"type": "string", "enum": ["salary","utilities","supplies","maintenance","transport","other"]},
                "paid_from": {"type": "string", "enum": ["cash", "bank"]},
                "note":      {"type": "string"},
            },
            "required": ["title", "amount", "category", "paid_from"],
        },
    },
    {
        "name": "create_teacher",
        "description": "Create a teacher account. Pick a memorable initial password the teacher can change later.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":            {"type": "string"},
                "email":           {"type": "string"},
                "password":        {"type": "string"},
                "employee_id":     {"type": "string"},
                "subject":         {"type": "string"},
                "classes_taught":  {"type": "string", "description": "comma-separated, e.g. '5,6,7'"},
                "qualification":   {"type": "string"},
                "phone":           {"type": "string"},
                "can_do_front_office": {"type": "boolean", "default": False},
            },
            "required": ["name", "email", "password", "employee_id"],
        },
    },
    {
        "name": "set_teacher_front_office",
        "description": "Grant or revoke a teacher's permission to use the front-office tile dashboard.",
        "input_schema": {
            "type": "object",
            "properties": {
                "teacher_id": {"type": "integer"},
                "enabled":    {"type": "boolean"},
            },
            "required": ["teacher_id", "enabled"],
        },
    },
    {
        "name": "delete_teacher",
        "description": "DESTRUCTIVE. Remove a teacher and their login.",
        "input_schema": {
            "type": "object",
            "properties": {"teacher_id": {"type": "integer"}},
            "required": ["teacher_id"],
        },
    },
    {
        "name": "create_assignment",
        "description": "Create an assignment for a class.",
        "input_schema": {
            "type": "object",
            "properties": {
                "teacher_id":    {"type": "integer"},
                "student_class": {"type": "string"},
                "section":       {"type": "string"},
                "subject":       {"type": "string"},
                "title":         {"type": "string"},
                "description":   {"type": "string"},
                "due_date":      {"type": "string", "description": "YYYY-MM-DD"},
                "max_marks":     {"type": "number", "default": 10},
            },
            "required": ["teacher_id", "student_class", "subject", "title"],
        },
    },
    {
        "name": "create_exam",
        "description": "Define an exam for a class. Doesn't enter marks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":          {"type": "string", "description": "e.g. 'Term 2'"},
                "academic_year": {"type": "string"},
                "student_class": {"type": "string"},
                "date":          {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["name", "academic_year", "student_class"],
        },
    },
]


READONLY = {
    "list_students", "get_student", "list_teachers", "list_fee_structures",
    "list_assignments", "get_dashboard_stats", "list_top_dues",
    "list_recent_payments", "list_recent_expenses",
}
DESTRUCTIVE = {"delete_student", "delete_teacher"}


# -----------------------------------------------------------------------
# Tool implementations
# -----------------------------------------------------------------------

def _t_list_students(db, student_class=None, search=None, limit=20):
    from sqlalchemy import or_
    q = db.query(models.Student)
    if student_class:
        q = q.filter(models.Student.student_class == student_class)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(models.Student.name.ilike(like),
                          models.Student.admission_no.ilike(like)))
    rows = q.limit(limit).all()
    return {"count": len(rows), "students": [
        {"id": s.id, "admission_no": s.admission_no, "name": s.name,
         "class": s.student_class, "section": s.section,
         "parent": s.parent_name, "phone": s.phone}
        for s in rows]}


def _t_get_student(db, student_id):
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s: raise ValueError(f"student {student_id} not found")
    total_fee = sum(f.total_fee for f in s.fees) + (s.last_year_dues or 0)
    paid = sum(p.amount for p in s.payments)
    return {
        "id": s.id, "admission_no": s.admission_no, "name": s.name,
        "class": s.student_class, "section": s.section,
        "aadhaar": s.aadhaar, "parent": s.parent_name, "phone": s.phone,
        "address": s.address, "status": s.status,
        "total_fee": total_fee, "paid": paid,
        "due": max(0, total_fee - paid),
        "last_year_dues": s.last_year_dues or 0,
    }


def _t_list_teachers(db):
    rows = db.query(models.Teacher).all()
    out = []
    for t in rows:
        u = db.query(models.User).filter(models.User.id == t.user_id).first()
        out.append({
            "id": t.id, "employee_id": t.employee_id,
            "name": u.name if u else "", "email": u.email if u else "",
            "subject": t.subject, "classes_taught": t.classes_taught,
            "can_do_front_office": u.can_do_front_office if u else False,
        })
    return {"count": len(out), "teachers": out}


def _t_list_fee_structures(db, student_class=None, academic_year=None):
    q = db.query(models.FeeStructure)
    if student_class: q = q.filter(models.FeeStructure.student_class == student_class)
    if academic_year: q = q.filter(models.FeeStructure.academic_year == academic_year)
    rows = q.all()
    return {"structures": [{
        "id": fs.id, "class": fs.student_class, "year": fs.academic_year,
        "tuition": fs.tuition_fee, "transport": fs.transport_fee,
        "books": fs.books_fee, "uniform": fs.uniform_fee, "other": fs.other_fee,
        "total": fs.tuition_fee + fs.transport_fee + fs.books_fee
                  + fs.uniform_fee + fs.other_fee,
    } for fs in rows]}


def _t_list_assignments(db, student_class=None, limit=25):
    q = db.query(models.Assignment)
    if student_class: q = q.filter(models.Assignment.student_class == student_class)
    rows = q.order_by(models.Assignment.id.desc()).limit(limit).all()
    return {"assignments": [{
        "id": a.id, "title": a.title, "subject": a.subject,
        "class": a.student_class, "section": a.section,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "max_marks": a.max_marks,
    } for a in rows]}


def _t_get_dashboard_stats(db):
    from sqlalchemy import func
    n = db.query(func.count(models.Student.id)).scalar() or 0
    paid = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)).scalar() or 0.0
    fee_total = db.query(func.coalesce(func.sum(models.Fee.total_fee), 0.0)).scalar() or 0.0
    last_year = db.query(func.coalesce(func.sum(models.Student.last_year_dues), 0.0)).scalar() or 0.0
    expense = db.query(func.coalesce(func.sum(models.Expense.amount), 0.0)).scalar() or 0.0
    cash_open = db.query(func.coalesce(func.sum(models.Account.opening_balance), 0.0)) \
                  .filter(models.Account.name == "cash").scalar() or 0.0
    bank_open = db.query(func.coalesce(func.sum(models.Account.opening_balance), 0.0)) \
                  .filter(models.Account.name == "bank").scalar() or 0.0
    cash_pay = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)) \
                 .filter(models.Payment.mode == "cash").scalar() or 0.0
    bank_pay = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)) \
                 .filter(models.Payment.mode == "bank").scalar() or 0.0
    cash_exp = db.query(func.coalesce(func.sum(models.Expense.amount), 0.0)) \
                 .filter(models.Expense.paid_from == "cash").scalar() or 0.0
    bank_exp = db.query(func.coalesce(func.sum(models.Expense.amount), 0.0)) \
                 .filter(models.Expense.paid_from == "bank").scalar() or 0.0
    return {
        "students": n,
        "total_billed": fee_total + last_year,
        "collected": paid,
        "due": max(0.0, fee_total + last_year - paid),
        "expense": expense,
        "net": paid - expense,
        "cash_balance": cash_open + cash_pay - cash_exp,
        "bank_balance": bank_open + bank_pay - bank_exp,
    }


def _t_list_top_dues(db, limit=10, min_due=0):
    students = db.query(models.Student).filter(models.Student.status == "active").all()
    rows = []
    for s in students:
        tot = sum(f.total_fee for f in s.fees) + (s.last_year_dues or 0)
        paid = sum(p.amount for p in s.payments)
        due = max(0, tot - paid)
        if due >= (min_due or 0) and due > 0:
            rows.append({"id": s.id, "name": s.name, "admission_no": s.admission_no,
                          "class": s.student_class, "section": s.section,
                          "due": due, "phone": s.phone, "parent": s.parent_name})
    rows.sort(key=lambda r: r["due"], reverse=True)
    return {"top_dues": rows[:limit]}


def _t_list_recent_payments(db, limit=20):
    rows = db.query(models.Payment).order_by(
        models.Payment.id.desc()).limit(limit).all()
    out = []
    for p in rows:
        s = db.query(models.Student).filter(models.Student.id == p.student_id).first()
        out.append({
            "id": p.id, "student_id": p.student_id,
            "student_name": s.name if s else "?",
            "amount": p.amount, "mode": p.mode, "fee_head": p.fee_head,
            "date": p.date.isoformat(),
        })
    return {"payments": out}


def _t_list_recent_expenses(db, limit=20):
    rows = db.query(models.Expense).order_by(
        models.Expense.id.desc()).limit(limit).all()
    return {"expenses": [{
        "id": e.id, "title": e.title, "amount": e.amount,
        "category": e.category, "paid_from": e.paid_from,
        "date": e.date.isoformat(),
    } for e in rows]}


def _t_create_student(db, **fields):
    if db.query(models.Student).filter(
        models.Student.admission_no == fields["admission_no"]).first():
        raise ValueError(f"admission_no {fields['admission_no']!r} already exists")
    s = models.Student(**fields)
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "name": s.name, "admission_no": s.admission_no,
            "class": s.student_class}


def _t_update_student(db, student_id, fields):
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s: raise ValueError(f"student {student_id} not found")
    changed = {}
    for k, v in fields.items():
        if hasattr(s, k):
            changed[k] = v
            setattr(s, k, v)
    db.commit()
    return {"id": s.id, "updated": changed}


def _t_delete_student(db, student_id):
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s: raise ValueError(f"student {student_id} not found")
    summary = {"id": s.id, "name": s.name, "admission_no": s.admission_no,
                "fee_rows_removed": len(s.fees),
                "payments_removed":  len(s.payments)}
    db.delete(s); db.commit()
    return {"deleted": summary}


def _t_set_student_status(db, student_id, status):
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s: raise ValueError(f"student {student_id} not found")
    s.status = status; db.commit()
    return {"id": s.id, "status": s.status}


def _t_create_fee_structure(db, **fields):
    existing = db.query(models.FeeStructure).filter(
        models.FeeStructure.student_class == fields["student_class"],
        models.FeeStructure.academic_year == fields["academic_year"],
    ).first()
    if existing:
        raise ValueError(
            f"a fee structure for class {fields['student_class']} in "
            f"{fields['academic_year']} already exists (id={existing.id}). "
            f"Use update_fee_structure instead.")
    fs = models.FeeStructure(**fields)
    db.add(fs); db.commit(); db.refresh(fs)
    return {"id": fs.id, "class": fs.student_class, "year": fs.academic_year,
            "total": fs.tuition_fee + fs.transport_fee + fs.books_fee
                      + fs.uniform_fee + fs.other_fee}


def _t_update_fee_structure(db, structure_id, fields):
    fs = db.query(models.FeeStructure).filter(
        models.FeeStructure.id == structure_id).first()
    if not fs: raise ValueError(f"fee structure {structure_id} not found")
    for k, v in fields.items():
        if hasattr(fs, k): setattr(fs, k, v)
    db.commit()
    return {"id": fs.id, "updated": fields}


def _t_apply_fee_structure(db, structure_id):
    fs = db.query(models.FeeStructure).filter(
        models.FeeStructure.id == structure_id).first()
    if not fs: raise ValueError(f"fee structure {structure_id} not found")
    total = fs.tuition_fee + fs.transport_fee + fs.books_fee \
            + fs.uniform_fee + fs.other_fee
    students = db.query(models.Student).filter(
        models.Student.student_class == fs.student_class,
        models.Student.status == "active").all()
    created = 0
    for s in students:
        if db.query(models.Fee).filter(
            models.Fee.student_id == s.id,
            models.Fee.academic_year == fs.academic_year).first():
            continue
        db.add(models.Fee(student_id=s.id, academic_year=fs.academic_year,
                          total_fee=total, paid_amount=0, due_amount=total))
        created += 1
    db.commit()
    return {"bills_created": created, "class": fs.student_class}


def _t_record_payment(db, **fields):
    if fields["amount"] <= 0:
        raise ValueError("amount must be greater than zero")
    if fields["mode"] not in ("cash", "bank"):
        raise ValueError("mode must be 'cash' or 'bank'")
    student = db.query(models.Student).filter(
        models.Student.id == fields["student_id"]).first()
    if not student: raise ValueError(f"student {fields['student_id']} not found")
    if "fee_head" not in fields: fields["fee_head"] = "Assistant"
    p = models.Payment(date=Date.today(), **fields)
    db.add(p)
    # Settle vs fees, then last_year_dues
    remaining = float(p.amount)
    for f in db.query(models.Fee).filter(models.Fee.student_id == p.student_id,
                                          models.Fee.due_amount > 0) \
                                  .order_by(models.Fee.id).all():
        if remaining <= 0: break
        applied = min(remaining, f.due_amount)
        f.paid_amount += applied
        f.due_amount -= applied
        remaining -= applied
    if remaining > 0 and (student.last_year_dues or 0) > 0:
        applied = min(remaining, student.last_year_dues)
        student.last_year_dues -= applied
    db.commit(); db.refresh(p)
    return {"payment_id": p.id, "applied": p.amount, "student": student.name}


def _t_record_expense(db, **fields):
    if fields["amount"] <= 0:
        raise ValueError("amount must be greater than zero")
    if fields["paid_from"] not in ("cash", "bank"):
        raise ValueError("paid_from must be 'cash' or 'bank'")
    e = models.Expense(date=Date.today(), **fields)
    db.add(e); db.commit(); db.refresh(e)
    return {"expense_id": e.id, "amount": e.amount}


def _t_create_teacher(db, **fields):
    if db.query(models.User).filter(models.User.email == fields["email"]).first():
        raise ValueError(f"email {fields['email']!r} is already in use")
    if db.query(models.Teacher).filter(
        models.Teacher.employee_id == fields["employee_id"]).first():
        raise ValueError(f"employee_id {fields['employee_id']!r} is already in use")
    can_front = fields.pop("can_do_front_office", False)
    pwd = fields.pop("password")
    user = models.User(
        name=fields.pop("name"), email=fields.pop("email"),
        password=auth.hash_password(pwd),
        role="teacher", status="active",
        can_do_front_office=can_front,
    )
    db.add(user); db.commit(); db.refresh(user)
    t = models.Teacher(user_id=user.id, **fields)
    db.add(t); db.commit(); db.refresh(t)
    return {"teacher_id": t.id, "user_id": user.id, "name": user.name,
            "email": user.email}


def _t_set_teacher_front_office(db, teacher_id, enabled):
    t = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if not t: raise ValueError(f"teacher {teacher_id} not found")
    u = db.query(models.User).filter(models.User.id == t.user_id).first()
    if u: u.can_do_front_office = bool(enabled)
    db.commit()
    return {"teacher_id": t.id, "can_do_front_office": bool(enabled)}


def _t_delete_teacher(db, teacher_id):
    t = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if not t: raise ValueError(f"teacher {teacher_id} not found")
    u = db.query(models.User).filter(models.User.id == t.user_id).first()
    info = {"teacher_id": t.id, "name": u.name if u else "?",
             "email": u.email if u else "?"}
    db.delete(t)
    if u: db.delete(u)
    db.commit()
    return {"deleted": info}


def _t_create_assignment(db, **fields):
    if not db.query(models.Teacher).filter(
        models.Teacher.id == fields["teacher_id"]).first():
        raise ValueError(f"teacher {fields['teacher_id']} not found")
    if isinstance(fields.get("due_date"), str):
        try: fields["due_date"] = Date.fromisoformat(fields["due_date"])
        except Exception: fields["due_date"] = None
    a = models.Assignment(**fields)
    db.add(a); db.commit(); db.refresh(a)
    return {"id": a.id, "title": a.title}


def _t_create_exam(db, **fields):
    if isinstance(fields.get("date"), str):
        try: fields["date"] = Date.fromisoformat(fields["date"])
        except Exception: fields["date"] = None
    e = models.Exam(**fields)
    db.add(e); db.commit(); db.refresh(e)
    return {"exam_id": e.id, "name": e.name}


TOOL_IMPLS = {
    "list_students":            _t_list_students,
    "get_student":              _t_get_student,
    "list_teachers":            _t_list_teachers,
    "list_fee_structures":      _t_list_fee_structures,
    "list_assignments":         _t_list_assignments,
    "get_dashboard_stats":      _t_get_dashboard_stats,
    "list_top_dues":            _t_list_top_dues,
    "list_recent_payments":     _t_list_recent_payments,
    "list_recent_expenses":     _t_list_recent_expenses,
    "create_student":           _t_create_student,
    "update_student":           _t_update_student,
    "delete_student":           _t_delete_student,
    "set_student_status":       _t_set_student_status,
    "create_fee_structure":     _t_create_fee_structure,
    "update_fee_structure":     _t_update_fee_structure,
    "apply_fee_structure":      _t_apply_fee_structure,
    "record_payment":           _t_record_payment,
    "record_expense":           _t_record_expense,
    "create_teacher":           _t_create_teacher,
    "set_teacher_front_office": _t_set_teacher_front_office,
    "delete_teacher":           _t_delete_teacher,
    "create_assignment":        _t_create_assignment,
    "create_exam":              _t_create_exam,
}


# -----------------------------------------------------------------------
# Anthropic API call
# -----------------------------------------------------------------------

def _call_claude(messages: list[dict]) -> dict:
    if not ANTHROPIC_KEY:
        raise HTTPException(503,
            "Assistant not configured. Set the ANTHROPIC_API_KEY env var "
            "and restart the backend.")
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1500,
        "system": SYSTEM_PROMPT.format(today=Date.today().isoformat()),
        "tools": TOOLS,
        "messages": messages,
    }).encode()
    req = urllib.request.Request(
        ANTHROPIC_URL, data=body,
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: detail = json.loads(e.read().decode())
        except Exception: detail = {"error": e.reason}
        raise HTTPException(502, f"Assistant API error {e.code}: {detail}")


def _conversation_to_messages(db: Session, conv_id: int) -> list[dict]:
    msgs = db.query(models.AIMessage).filter(
        models.AIMessage.conversation_id == conv_id
    ).order_by(models.AIMessage.id).all()
    out = []
    for m in msgs:
        if m.role == "user":
            out.append({"role": "user", "content": m.content})
        else:
            blocks = [{"type": "text", "text": m.content}] if m.content else []
            if m.actions:
                try:
                    for a in json.loads(m.actions):
                        blocks.append({
                            "type": "tool_use",
                            "id": a["id"], "name": a["name"], "input": a["input"],
                        })
                except Exception:
                    pass
            out.append({"role": "assistant",
                         "content": blocks or [{"type": "text", "text": ""}]})
    return out


# -----------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------

@router.get("/conversations", response_model=list[schemas.AIConversationOut])
def list_conversations(db: Session = Depends(get_db),
                       owner: models.User = Depends(require_owner)):
    return db.query(models.AIConversation).filter(
        models.AIConversation.user_id == owner.id
    ).order_by(models.AIConversation.id.desc()).all()


@router.get("/conversations/{conv_id}/messages",
            response_model=list[schemas.AIMessageOut])
def conversation_messages(conv_id: int,
                          db: Session = Depends(get_db),
                          owner: models.User = Depends(require_owner)):
    conv = db.query(models.AIConversation).filter(
        models.AIConversation.id == conv_id,
        models.AIConversation.user_id == owner.id).first()
    if not conv: raise HTTPException(404, "Conversation not found")
    return db.query(models.AIMessage).filter(
        models.AIMessage.conversation_id == conv_id
    ).order_by(models.AIMessage.id).all()


@router.post("/chat")
def chat(payload: schemas.AIChatIn,
         db: Session = Depends(get_db),
         owner: models.User = Depends(require_owner)):
    """Send a message. Returns the assistant's reply with optional proposed actions."""
    if payload.conversation_id:
        conv = db.query(models.AIConversation).filter(
            models.AIConversation.id == payload.conversation_id,
            models.AIConversation.user_id == owner.id).first()
        if not conv: raise HTTPException(404, "Conversation not found")
    else:
        title = payload.message[:60] + ("…" if len(payload.message) > 60 else "")
        conv = models.AIConversation(user_id=owner.id, title=title)
        db.add(conv); db.commit(); db.refresh(conv)

    user_msg = models.AIMessage(conversation_id=conv.id, role="user",
                                  content=payload.message)
    db.add(user_msg); db.commit()

    messages = _conversation_to_messages(db, conv.id)
    response = _call_claude(messages)

    text_parts, actions = [], []
    for block in response.get("content", []):
        if block["type"] == "text":
            text_parts.append(block["text"])
        elif block["type"] == "tool_use":
            actions.append({
                "id": block["id"],
                "name": block["name"],
                "input": block["input"],
                "destructive": block["name"] in DESTRUCTIVE,
                "readonly":    block["name"] in READONLY,
            })
    text = "\n\n".join(text_parts).strip()
    if not text and actions:
        text = "I'd like to perform the actions below — please review and confirm."

    asst_msg = models.AIMessage(
        conversation_id=conv.id, role="assistant",
        content=text,
        actions=json.dumps(actions) if actions else None,
        executed=False,
    )
    db.add(asst_msg); db.commit(); db.refresh(asst_msg)

    return {
        "conversation_id": conv.id,
        "message_id": asst_msg.id,
        "text": text,
        "actions": actions,
    }


@router.post("/execute")
def execute(payload: dict,
            db: Session = Depends(get_db),
            owner: models.User = Depends(require_owner)):
    """
    Run only the actions Owner approved. Body:
        { conversation_id, message_id, approved_action_ids: [str], overrides: {id: input_obj} }
    `overrides` lets Owner tweak inputs before applying.
    """
    conv_id    = payload.get("conversation_id")
    msg_id     = payload.get("message_id")
    approved   = set(payload.get("approved_action_ids") or [])
    overrides  = payload.get("overrides") or {}

    msg = db.query(models.AIMessage).filter(
        models.AIMessage.id == msg_id,
        models.AIMessage.conversation_id == conv_id,
    ).first()
    if not msg or msg.role != "assistant":
        raise HTTPException(404, "Message not found")
    if msg.executed:
        raise HTTPException(400, "These actions have already been executed.")
    if not msg.actions:
        raise HTTPException(400, "There are no actions to execute on this message.")

    actions = json.loads(msg.actions)
    if not approved:
        raise HTTPException(400, "Pick at least one action to apply.")

    results = []
    for a in actions:
        if a["id"] not in approved:
            results.append({"name": a["name"], "id": a["id"],
                             "ok": True, "skipped": True})
            continue
        impl = TOOL_IMPLS.get(a["name"])
        if not impl:
            results.append({"name": a["name"], "id": a["id"],
                             "ok": False, "error": "unknown tool"})
            continue
        args = overrides.get(a["id"], a["input"])
        try:
            res = impl(db, **args)
            results.append({"name": a["name"], "id": a["id"],
                             "ok": True, "result": res})
        except Exception as e:
            results.append({"name": a["name"], "id": a["id"],
                             "ok": False, "error": str(e)})

    msg.executed = True
    db.commit()

    summary = "\n".join(
        f"  • {r['name']}: " + ("(skipped)" if r.get("skipped")
            else ("✓ " + json.dumps(r['result']) if r.get('ok')
                                                else "✗ " + r.get('error', '?')))
        for r in results
    )
    db.add(models.AIMessage(
        conversation_id=conv_id, role="user",
        content=f"[system] Result of {len(approved)} approved action(s):\n{summary}",
    ))
    db.commit()
    return {"results": results}


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int,
                        db: Session = Depends(get_db),
                        owner: models.User = Depends(require_owner)):
    conv = db.query(models.AIConversation).filter(
        models.AIConversation.id == conv_id,
        models.AIConversation.user_id == owner.id).first()
    if not conv: raise HTTPException(404, "Not found")
    db.query(models.AIMessage).filter(models.AIMessage.conversation_id == conv_id).delete()
    db.delete(conv); db.commit()
    return {"ok": True}


@router.get("/status")
def status():
    return {
        "configured": bool(ANTHROPIC_KEY),
        "model": ANTHROPIC_MODEL if ANTHROPIC_KEY else None,
        "tools_count": len(TOOLS),
    }


@router.get("/tools")
def list_tools(_owner: models.User = Depends(require_owner)):
    """Surface what the assistant CAN do (helpful for the Owner)."""
    return [{
        "name": t["name"], "description": t["description"],
        "destructive": t["name"] in DESTRUCTIVE,
        "readonly":    t["name"] in READONLY,
    } for t in TOOLS]
