"""
Fees — fee structures, bills, payments, and printable receipts.

I own fee structures, bills, payments, and printable receipts.
My money flow rules (the only ones that matter):

  total_fee_for_student   = sum(this-year fee bills) + last_year_dues
  total_paid_for_student  = sum(payments)
  outstanding_for_student = max(0, total_fee_for_student - total_paid_for_student)
  credit_for_student      = max(0, total_paid_for_student - total_fee_for_student)

When a payment comes in we settle it against the oldest outstanding fee row
first, then against last_year_dues. Any leftover sits as a credit on the
student (visible in the student detail).

Cash + bank balances are NOT stored — the Finance agent computes them live
from `opening_balance + sum(payments[mode]) - sum(expenses[paid_from])`. So
recording any payment or expense automatically updates every dashboard.
"""

from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import (
    get_db, require_owner, require_can_collect,
)
from school_constants import class_sort_key, PAYMENT_MODES

SCHOOL_NAME = "Sage"

router = APIRouter(tags=["fees"])


# ---------- Fee structures (Owner only) ---------- #

@router.get("/fee-structures", response_model=list[schemas.FeeStructureOut])
def list_structures(db: Session = Depends(get_db),
                    _owner: models.User = Depends(require_owner)):
    rows = db.query(models.FeeStructure).all()
    rows.sort(key=lambda fs: (-int(fs.academic_year[:4]),  # newest year first
                              class_sort_key(fs.student_class)))
    return rows


@router.post("/fee-structures", response_model=schemas.FeeStructureOut)
def create_structure(payload: schemas.FeeStructureCreate,
                     db: Session = Depends(get_db),
                     _owner: models.User = Depends(require_owner)):
    # Don't let two structures exist for the same class+year
    existing = db.query(models.FeeStructure).filter(
        models.FeeStructure.student_class == payload.student_class,
        models.FeeStructure.academic_year == payload.academic_year,
    ).first()
    if existing:
        raise HTTPException(
            400,
            f"A fee structure for class {payload.student_class} in "
            f"{payload.academic_year} already exists. Edit that one instead."
        )
    fs = models.FeeStructure(**payload.model_dump())
    db.add(fs); db.commit(); db.refresh(fs)
    return fs


@router.post("/fee-structures/{structure_id}/apply")
def apply_structure(structure_id: int,
                    db: Session = Depends(get_db),
                    _owner: models.User = Depends(require_owner)):
    """Generate a fee bill for every active student in this structure's class."""
    fs = db.query(models.FeeStructure).filter(models.FeeStructure.id == structure_id).first()
    if not fs:
        raise HTTPException(404, "Fee structure not found")

    total = (fs.tuition_fee + fs.transport_fee + fs.books_fee
             + fs.uniform_fee + fs.other_fee)

    students = db.query(models.Student).filter(
        models.Student.student_class == fs.student_class,
        models.Student.status == "active",
    ).all()

    created = 0
    for s in students:
        already = db.query(models.Fee).filter(
            models.Fee.student_id == s.id,
            models.Fee.academic_year == fs.academic_year,
        ).first()
        if already:
            continue
        db.add(models.Fee(
            student_id=s.id,
            academic_year=fs.academic_year,
            total_fee=total,
            paid_amount=0,
            due_amount=total,
        ))
        created += 1
    db.commit()
    return {"created": created, "class": fs.student_class, "year": fs.academic_year}


# ---------- Per-student bills (Owner only) ---------- #

@router.get("/fees", response_model=list[schemas.FeeOut])
def list_fees(student_id: int | None = None,
              db: Session = Depends(get_db),
              _owner: models.User = Depends(require_owner)):
    q = db.query(models.Fee)
    if student_id is not None:
        q = q.filter(models.Fee.student_id == student_id)
    return q.order_by(models.Fee.academic_year.desc()).all()


@router.post("/fees", response_model=schemas.FeeOut)
def create_fee(payload: schemas.FeeCreate,
               db: Session = Depends(get_db),
               _owner: models.User = Depends(require_owner)):
    if not db.query(models.Student).filter(models.Student.id == payload.student_id).first():
        raise HTTPException(400, "Student not found")
    fee = models.Fee(
        student_id=payload.student_id,
        academic_year=payload.academic_year,
        total_fee=payload.total_fee,
        paid_amount=0,
        due_amount=payload.total_fee,
        due_date=payload.due_date,
    )
    db.add(fee); db.commit(); db.refresh(fee)
    return fee


# ---------- Payments ---------- #

@router.get("/payments", response_model=list[schemas.PaymentOut])
def list_payments(student_id: int | None = None,
                  limit: int = 50,
                  db: Session = Depends(get_db),
                  _owner: models.User = Depends(require_owner)):
    q = db.query(models.Payment)
    if student_id is not None:
        q = q.filter(models.Payment.student_id == student_id)
    return q.order_by(models.Payment.date.desc(), models.Payment.id.desc()).limit(limit).all()


@router.post("/payments", response_model=schemas.PaymentOut)
def make_payment(payload: schemas.PaymentCreate,
                 db: Session = Depends(get_db),
                 user: models.User = Depends(require_can_collect)):
    # ----- Input checks ----- #
    if payload.amount is None or payload.amount <= 0:
        raise HTTPException(400, "Payment amount must be greater than zero.")
    if payload.mode not in PAYMENT_MODES:
        raise HTTPException(400, "Payment mode must be either 'cash' or 'bank'.")

    student = db.query(models.Student).filter(
        models.Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(400, "Student not found.")

    # ----- Record the payment ----- #
    payment = models.Payment(
        student_id=payload.student_id,
        amount=float(payload.amount),
        date=payload.date or date.today(),
        mode=payload.mode,
        fee_head=payload.fee_head,
        reference=payload.reference,
        note=payload.note,
        received_by=user.id,
    )
    db.add(payment)

    # ----- Settle against dues, oldest first ----- #
    remaining = float(payload.amount)

    # 1. This year's fee bills (oldest id first).
    open_fees = db.query(models.Fee).filter(
        models.Fee.student_id == payload.student_id,
        models.Fee.due_amount > 0,
    ).order_by(models.Fee.id).all()
    for f in open_fees:
        if remaining <= 0:
            break
        applied = min(remaining, f.due_amount)
        f.paid_amount += applied
        f.due_amount -= applied
        remaining -= applied

    # 2. Last-year carry-forward dues.
    if remaining > 0 and (student.last_year_dues or 0) > 0:
        applied = min(remaining, student.last_year_dues)
        student.last_year_dues -= applied
        remaining -= applied

    # 3. Anything left is a credit on the student. We don't reject overpayment
    #    — sometimes parents pay round numbers — but we keep it visible in the
    #    student detail view (paid > total_billed).

    db.commit()
    db.refresh(payment)
    return payment


# ---------- Printable receipt ---------- #

def _money(n: float) -> str:
    return "₹ " + f"{n:,.0f}"


def _receipt_html(payment: models.Payment, student: models.Student,
                  school_name: str = SCHOOL_NAME) -> str:
    issued = datetime.utcnow().strftime("%d %b %Y, %H:%M")
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>Receipt #{payment.id} — {student.name}</title>
<style>
  @page {{ size: A5; margin: 14mm; }}
  body {{ font-family: -apple-system, "Segoe UI", Arial, sans-serif; color: #111;
         max-width: 460px; margin: 18px auto; }}
  .head {{ text-align: center; border-bottom: 2px solid #111; padding-bottom: 12px; margin-bottom: 16px; }}
  .head h1 {{ margin: 0; font-size: 20px; letter-spacing: .02em; }}
  .head .sub {{ font-size: 11px; color: #666; margin-top: 4px; }}
  .meta {{ display: flex; justify-content: space-between; font-size: 12px;
          color: #444; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table td {{ padding: 6px 0; }}
  table .label {{ color: #666; width: 45%; }}
  table .val {{ text-align: right; font-weight: 600; }}
  .amount {{ background: #f3f5fa; padding: 14px 16px; border-radius: 8px;
            margin: 18px 0; display: flex; justify-content: space-between;
            align-items: center; }}
  .amount .l {{ font-size: 12px; color: #666; }}
  .amount .v {{ font-size: 22px; font-weight: 700; }}
  .foot {{ border-top: 1px dashed #aaa; margin-top: 22px; padding-top: 12px;
          font-size: 11px; color: #666; text-align: center; }}
  .actions {{ text-align: center; margin: 16px 0 4px; }}
  .actions button {{ padding: 8px 18px; border: 1px solid #2f6bff; background: #2f6bff;
                    color: #fff; border-radius: 6px; font-size: 13px; cursor: pointer;
                    margin: 0 4px; font-weight: 600; }}
  .actions button.sec {{ background: #fff; color: #2f6bff; }}
  @media print {{ .actions {{ display: none; }} body {{ margin: 0; }} }}
</style>
</head><body>

<div class="head">
  <h1>{school_name}</h1>
  <div class="sub">FEE RECEIPT</div>
</div>

<div class="meta">
  <div>Receipt&nbsp;# <strong>{payment.id:06d}</strong></div>
  <div>{issued}</div>
</div>

<table>
  <tr><td class="label">Student name</td><td class="val">{student.name}</td></tr>
  <tr><td class="label">Admission no.</td><td class="val">{student.admission_no}</td></tr>
  <tr><td class="label">Class</td><td class="val">{student.student_class}{('-' + student.section) if student.section else ''}</td></tr>
  <tr><td class="label">Parent / guardian</td><td class="val">{student.parent_name or '—'}</td></tr>
  <tr><td class="label">Date</td><td class="val">{payment.date.strftime('%d %b %Y')}</td></tr>
  <tr><td class="label">Mode</td><td class="val">{payment.mode.upper()}</td></tr>
  <tr><td class="label">Fee head</td><td class="val">{payment.fee_head or 'General'}</td></tr>
  {f'<tr><td class="label">Reference</td><td class="val">{payment.reference}</td></tr>' if payment.reference else ''}
</table>

<div class="amount">
  <div class="l">AMOUNT RECEIVED</div>
  <div class="v">{_money(payment.amount)}</div>
</div>

<div class="actions">
  <button onclick="window.print()">🖨 Print / Save as PDF</button>
  <button class="sec" onclick="window.close()">Close</button>
</div>

<div class="foot">
  This is a system-generated receipt and does not require a signature.<br/>
  Thank you.
</div>

<script>
  window.addEventListener('load', () => setTimeout(() => window.print(), 250));
</script>
</body></html>"""


@router.get("/payments/{payment_id}/receipt", response_class=HTMLResponse)
def receipt(payment_id: int,
            db: Session = Depends(get_db),
            _user: models.User = Depends(require_can_collect)):
    p = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not p:
        raise HTTPException(404, "Payment not found")
    s = db.query(models.Student).filter(models.Student.id == p.student_id).first()
    if not s:
        raise HTTPException(404, "Student not found")
    return HTMLResponse(_receipt_html(p, s))
