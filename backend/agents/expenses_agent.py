"""
Expenses Agent — v0.3.

Owner: GET / DELETE.
Staff or Owner: POST (tile-driven expense entry).
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import (
    get_db, require_owner, require_can_collect,
)

router = APIRouter(prefix="/expenses", tags=["expenses"])

SCHOOL_NAME = "Sage"
VALID_CATEGORIES = {"salary", "utilities", "supplies", "maintenance", "transport", "other"}


@router.get("", response_model=list[schemas.ExpenseOut])
def list_expenses(db: Session = Depends(get_db),
                  _owner: models.User = Depends(require_owner)):
    return db.query(models.Expense).order_by(
        models.Expense.date.desc(), models.Expense.id.desc()
    ).all()


@router.post("", response_model=schemas.ExpenseOut)
def create_expense(payload: schemas.ExpenseCreate,
                   db: Session = Depends(get_db),
                   user: models.User = Depends(require_can_collect)):
    # Strict input validation — bad data here corrupts cash + bank balances.
    if payload.amount is None or payload.amount <= 0:
        raise HTTPException(400, "Expense amount must be greater than zero.")
    if payload.paid_from not in ("cash", "bank"):
        raise HTTPException(400, "Paid-from must be either 'cash' or 'bank'.")
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(
            400,
            f"Category must be one of: {', '.join(sorted(VALID_CATEGORIES))}.")
    if not (payload.title or "").strip():
        raise HTTPException(400, "Expense needs a title.")
    e = models.Expense(
        title=payload.title.strip(),
        amount=float(payload.amount),
        category=payload.category,
        paid_from=payload.paid_from,
        date=payload.date,
        note=payload.note,
        created_by=user.id,
    )
    db.add(e); db.commit(); db.refresh(e)
    return e


@router.delete("/{expense_id}")
def delete_expense(expense_id: int,
                   db: Session = Depends(get_db),
                   _owner: models.User = Depends(require_owner)):
    e = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if not e:
        raise HTTPException(404, "Expense not found")
    db.delete(e)
    db.commit()
    return {"ok": True}


# ---------- Printable receipt ---------- #

def _money(n: float) -> str:
    return "₹ " + f"{n:,.0f}"


def _expense_receipt_html(e: models.Expense) -> str:
    issued = datetime.utcnow().strftime("%d %b %Y, %H:%M")
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>Expense voucher #{e.id} — {e.title}</title>
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
  .amount {{ background: #fff5f0; padding: 14px 16px; border-radius: 8px;
            margin: 18px 0; display: flex; justify-content: space-between;
            align-items: center; border-left: 4px solid #d97706; }}
  .amount .l {{ font-size: 12px; color: #666; }}
  .amount .v {{ font-size: 22px; font-weight: 700; color: #b45309; }}
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
  <h1>{SCHOOL_NAME}</h1>
  <div class="sub">EXPENSE VOUCHER</div>
</div>

<div class="meta">
  <div>Voucher&nbsp;# <strong>EXP{e.id:06d}</strong></div>
  <div>{issued}</div>
</div>

<table>
  <tr><td class="label">Description</td><td class="val">{e.title}</td></tr>
  <tr><td class="label">Category</td><td class="val">{e.category.title()}</td></tr>
  <tr><td class="label">Date</td><td class="val">{e.date.strftime('%d %b %Y')}</td></tr>
  <tr><td class="label">Paid from</td><td class="val">{e.paid_from.upper()}</td></tr>
  {f'<tr><td class="label">Note</td><td class="val">{e.note}</td></tr>' if e.note else ''}
</table>

<div class="amount">
  <div class="l">AMOUNT PAID</div>
  <div class="v">− {_money(e.amount)}</div>
</div>

<div class="actions">
  <button onclick="window.print()">🖨 Print / Save as PDF</button>
  <button class="sec" onclick="window.close()">Close</button>
</div>

<div class="foot">
  This is a system-generated voucher and does not require a signature.
</div>

<script>
  window.addEventListener('load', () => setTimeout(() => window.print(), 250));
</script>
</body></html>"""


@router.get("/{expense_id}/receipt", response_class=HTMLResponse)
def expense_receipt(expense_id: int,
                    db: Session = Depends(get_db),
                    _user: models.User = Depends(require_can_collect)):
    e = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if not e:
        raise HTTPException(404, "Expense not found")
    return HTMLResponse(_expense_receipt_html(e))
