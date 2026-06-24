"""
Reports Agent — v0.4. Owner-only.
"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import schemas
from school_constants import month_bounds
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
    m_start, m_next = month_bounds(today)
    collected_today = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)) \
        .filter(models.Payment.date == today).scalar() or 0.0
    collected_month = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)) \
        .filter(models.Payment.date >= m_start, models.Payment.date < m_next).scalar() or 0.0

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
    # Bucket by YYYY-MM in Python so the grouping is DB-portable (no strftime).
    pay: dict[str, float] = {}
    for d, a in db.query(models.Payment.date, models.Payment.amount).all():
        if d:
            pay[d.strftime("%Y-%m")] = pay.get(d.strftime("%Y-%m"), 0.0) + float(a or 0)
    exp: dict[str, float] = {}
    for d, a in db.query(models.Expense.date, models.Expense.amount).all():
        if d:
            exp[d.strftime("%Y-%m")] = exp.get(d.strftime("%Y-%m"), 0.0) + float(a or 0)

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


@router.get("/at-risk", response_model=list[schemas.AtRiskStudent])
def at_risk(
    min_due: float = Query(1000, description="Minimum outstanding due (INR)"),
    days_without_payment: int = Query(30, description="Days since last payment"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """
    Students with outstanding dues and no recent payment activity.
    Risk score 0-100 based on due amount and payment inactivity.
    """
    today = date.today()
    cutoff = today - timedelta(days=days_without_payment)

    students = db.query(models.Student).filter(models.Student.status == "active").all()
    results = []

    for s in students:
        total_billed = sum(f.total_fee for f in s.fees) + (s.last_year_dues or 0)
        total_paid   = sum(p.amount for p in s.payments)
        due          = max(0.0, total_billed - total_paid)

        if due < min_due:
            continue

        last_pay_date = max((p.date for p in s.payments), default=None)
        days_since = (today - last_pay_date).days if last_pay_date else 999

        if days_since < days_without_payment:
            continue

        # Risk score: combines due magnitude and payment gap
        due_score  = min(50, int(due / 1000))          # up to 50 pts for amount
        days_score = min(50, int(days_since / 6))      # up to 50 pts for inactivity
        score      = min(100, due_score + days_score)

        if score >= 75:
            level = "critical"
        elif score >= 50:
            level = "high"
        elif score >= 25:
            level = "medium"
        else:
            level = "low"

        results.append(schemas.AtRiskStudent(
            id=s.id,
            admission_no=s.admission_no,
            name=s.name,
            student_class=s.student_class,
            section=s.section,
            parent_name=s.parent_name,
            phone=s.phone,
            due=round(due, 2),
            days_since_payment=days_since if last_pay_date else None,
            risk_score=score,
            risk_level=level,
        ))

    results.sort(key=lambda r: r.risk_score, reverse=True)
    return results[:limit]


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
