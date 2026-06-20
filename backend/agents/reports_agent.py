"""
Reports Agent — v0.3. Owner-only.
"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import schemas
from dependencies import get_db, require_owner

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard", response_model=schemas.DashboardOut)
def dashboard(db: Session = Depends(get_db),
              _owner: models.User = Depends(require_owner)):
    total_students = db.query(func.count(models.Student.id)).scalar() or 0
    active_students = db.query(func.count(models.Student.id)) \
        .filter(models.Student.status == "active").scalar() or 0

    total_fee_value = db.query(func.coalesce(func.sum(models.Fee.total_fee), 0.0)).scalar() or 0.0
    last_year_dues  = db.query(func.coalesce(func.sum(models.Student.last_year_dues), 0.0)).scalar() or 0.0
    total_collected = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)).scalar() or 0.0
    total_expense   = db.query(func.coalesce(func.sum(models.Expense.amount), 0.0)).scalar() or 0.0

    total_fee_value += last_year_dues
    # Never show a negative outstanding balance — overpayments don't reduce
    # the school's "still to collect" past zero.
    total_due = max(0.0, total_fee_value - total_collected)

    today = date.today()
    month_prefix = today.strftime("%Y-%m")
    collected_today = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)) \
        .filter(models.Payment.date == today).scalar() or 0.0
    collected_month = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)) \
        .filter(func.strftime("%Y-%m", models.Payment.date) == month_prefix).scalar() or 0.0

    def acct_balance(name: str) -> float:
        opening = db.query(func.coalesce(func.sum(models.Account.opening_balance), 0.0)) \
            .filter(models.Account.name == name).scalar() or 0.0
        pay = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)) \
            .filter(models.Payment.mode == name).scalar() or 0.0
        exp = db.query(func.coalesce(func.sum(models.Expense.amount), 0.0)) \
            .filter(models.Expense.paid_from == name).scalar() or 0.0
        return opening + pay - exp

    cash_balance = acct_balance("cash")
    bank_balance = acct_balance("bank")

    return schemas.DashboardOut(
        total_students=total_students,
        active_students=active_students,
        total_fee_value=total_fee_value,
        total_collected=total_collected,
        total_due=total_due,
        total_expense=total_expense,
        cash_balance=cash_balance,
        bank_balance=bank_balance,
        net=total_collected - total_expense,
        collected_today=collected_today,
        collected_this_month=collected_month,
    )


@router.get("/daily", response_model=list[schemas.DailyReportRow])
def daily(days: int = 30,
          db: Session = Depends(get_db),
          _owner: models.User = Depends(require_owner)):
    today = date.today()
    start = today - timedelta(days=days - 1)

    pay_rows = db.query(models.Payment.date, func.sum(models.Payment.amount)) \
        .filter(models.Payment.date >= start).group_by(models.Payment.date).all()
    exp_rows = db.query(models.Expense.date, func.sum(models.Expense.amount)) \
        .filter(models.Expense.date >= start).group_by(models.Expense.date).all()

    pay = {d: float(a) for d, a in pay_rows}
    exp = {d: float(a) for d, a in exp_rows}

    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        c = pay.get(d, 0.0)
        e = exp.get(d, 0.0)
        out.append(schemas.DailyReportRow(date=d, collected=c, expense=e, net=c - e))
    return out


@router.get("/monthly", response_model=list[schemas.MonthlyReportRow])
def monthly(months: int = 12,
            db: Session = Depends(get_db),
            _owner: models.User = Depends(require_owner)):
    pay = dict(db.query(
        func.strftime("%Y-%m", models.Payment.date),
        func.sum(models.Payment.amount),
    ).group_by(func.strftime("%Y-%m", models.Payment.date)).all())
    exp = dict(db.query(
        func.strftime("%Y-%m", models.Expense.date),
        func.sum(models.Expense.amount),
    ).group_by(func.strftime("%Y-%m", models.Expense.date)).all())

    today = date.today()
    out = []
    y, m = today.year, today.month
    seq = []
    for _ in range(months):
        seq.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    for key in reversed(seq):
        c = float(pay.get(key, 0) or 0)
        e = float(exp.get(key, 0) or 0)
        out.append(schemas.MonthlyReportRow(month=key, collected=c, expense=e, net=c - e))
    return out


@router.get("/yearly", response_model=list[schemas.YearlyReport])
def yearly(db: Session = Depends(get_db),
           _owner: models.User = Depends(require_owner)):
    years = [y for (y,) in db.query(models.Fee.academic_year).distinct().all()]
    out = []
    for y in years:
        total_fee = db.query(func.coalesce(func.sum(models.Fee.total_fee), 0.0)) \
            .filter(models.Fee.academic_year == y).scalar() or 0.0
        collected = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)).scalar() or 0.0
        expense = db.query(func.coalesce(func.sum(models.Expense.amount), 0.0)).scalar() or 0.0
        out.append(schemas.YearlyReport(
            academic_year=y,
            total_fee_value=total_fee,
            total_collected=collected,
            total_due=max(total_fee - collected, 0.0),
            total_expense=expense,
            net=collected - expense,
        ))
    return out
