"""
Finance Agent — v0.3. Owner-only views.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import schemas
from school_constants import month_bounds
from dependencies import get_db, require_owner

router = APIRouter(prefix="/finance", tags=["finance"])


def _balance(db: Session, name: str) -> tuple[models.Account, float]:
    acct = db.query(models.Account).filter(models.Account.name == name).first()
    if not acct:
        acct = models.Account(name=name, opening_balance=0)
        db.add(acct)
        db.commit()
        db.refresh(acct)

    payments_sum = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)) \
        .filter(models.Payment.mode == name).scalar() or 0.0
    expenses_sum = db.query(func.coalesce(func.sum(models.Expense.amount), 0.0)) \
        .filter(models.Expense.paid_from == name).scalar() or 0.0

    balance = (acct.opening_balance or 0) + payments_sum - expenses_sum
    return acct, balance


@router.get("/summary", response_model=schemas.FinanceSummary)
def summary(db: Session = Depends(get_db),
            _owner: models.User = Depends(require_owner)):
    cash_acct, cash_bal = _balance(db, "cash")
    bank_acct, bank_bal = _balance(db, "bank")
    today = date.today()
    m_start, m_next = month_bounds(today)

    today_collected = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)) \
        .filter(models.Payment.date == today).scalar() or 0.0
    month_collected = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)) \
        .filter(models.Payment.date >= m_start, models.Payment.date < m_next).scalar() or 0.0

    today_expense = db.query(func.coalesce(func.sum(models.Expense.amount), 0.0)) \
        .filter(models.Expense.date == today).scalar() or 0.0
    month_expense = db.query(func.coalesce(func.sum(models.Expense.amount), 0.0)) \
        .filter(models.Expense.date >= m_start, models.Expense.date < m_next).scalar() or 0.0

    return schemas.FinanceSummary(
        cash=schemas.AccountOut(
            name=cash_acct.name,
            opening_balance=cash_acct.opening_balance,
            balance=cash_bal,
        ),
        bank=schemas.AccountOut(
            name=bank_acct.name,
            opening_balance=bank_acct.opening_balance,
            balance=bank_bal,
        ),
        total_balance=cash_bal + bank_bal,
        total_collected_today=today_collected,
        total_collected_month=month_collected,
        total_expense_today=today_expense,
        total_expense_month=month_expense,
    )


@router.put("/accounts/{name}")
def update_opening_balance(name: str,
                           payload: schemas.AccountUpdate,
                           db: Session = Depends(get_db),
                           _owner: models.User = Depends(require_owner)):
    if name not in ("cash", "bank"):
        raise HTTPException(400, "account name must be 'cash' or 'bank'")
    acct, _ = _balance(db, name)
    acct.opening_balance = payload.opening_balance
    db.commit()
    db.refresh(acct)
    return {"ok": True, "opening_balance": acct.opening_balance}
