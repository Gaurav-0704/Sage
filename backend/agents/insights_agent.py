"""
Insights Agent — Proactive AI observations about school health.

I get called nightly by the scanner and on-demand by the owner.
I aggregate school metrics, send them to Claude with a focused analysis
prompt, and persist the structured results in the ai_insights table.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_db, require_owner

router = APIRouter(prefix="/insights", tags=["insights"])

ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_URL   = "https://api.anthropic.com/v1/messages"

ANALYSIS_PROMPT = (
    "You are analysing the financial and operational health of a school. "
    "You will receive a JSON snapshot of key metrics. Return a JSON array of insight objects. "
    "Each object must have exactly these keys: "
    "\"category\" (one of: finance, fees, academic, operations), "
    "\"severity\" (one of: info, warning, critical), "
    "\"title\" (short headline max 80 chars), "
    "\"body\" (1-3 sentences with specific numbers from the data), "
    "\"action_hint\" (a natural-language question the owner could ask the assistant to act on this). "
    "Rules: be specific with actual numbers; only flag genuinely noteworthy things; "
    "produce 4-8 insights ordered critical first; return ONLY the JSON array, no markdown."
)


def _build_snapshot(db: Session) -> dict:
    today = date.today()
    month_prefix = today.strftime("%Y-%m")
    prev_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    total_students  = db.query(func.count(models.Student.id)).scalar() or 0
    active_students = db.query(func.count(models.Student.id)).filter(
        models.Student.status == "active").scalar() or 0
    total_fee_billed = float(db.query(func.coalesce(func.sum(models.Fee.total_fee), 0)).scalar() or 0)
    last_yr_dues     = float(db.query(func.coalesce(func.sum(models.Student.last_year_dues), 0)).scalar() or 0)
    total_collected  = float(db.query(func.coalesce(func.sum(models.Payment.amount), 0)).scalar() or 0)
    total_expense    = float(db.query(func.coalesce(func.sum(models.Expense.amount), 0)).scalar() or 0)
    total_due        = max(0.0, total_fee_billed + last_yr_dues - total_collected)

    collected_month = float(db.query(func.coalesce(func.sum(models.Payment.amount), 0)).filter(
        func.strftime("%Y-%m", models.Payment.date) == month_prefix).scalar() or 0)
    collected_prev  = float(db.query(func.coalesce(func.sum(models.Payment.amount), 0)).filter(
        func.strftime("%Y-%m", models.Payment.date) == prev_month).scalar() or 0)
    expense_month   = float(db.query(func.coalesce(func.sum(models.Expense.amount), 0)).filter(
        func.strftime("%Y-%m", models.Expense.date) == month_prefix).scalar() or 0)
    expense_prev    = float(db.query(func.coalesce(func.sum(models.Expense.amount), 0)).filter(
        func.strftime("%Y-%m", models.Expense.date) == prev_month).scalar() or 0)

    cat_rows = db.query(
        models.Expense.category, func.sum(models.Expense.amount)
    ).filter(func.strftime("%Y-%m", models.Expense.date) == month_prefix
    ).group_by(models.Expense.category).all()
    expense_by_category = {c: round(float(a)) for c, a in cat_rows}

    all_active = db.query(models.Student).filter(models.Student.status == "active").all()
    high_risk = 0
    med_risk  = 0
    top_dues  = []
    for s in all_active:
        tot  = sum(f.total_fee for f in s.fees) + (s.last_year_dues or 0)
        paid = sum(p.amount for p in s.payments)
        due  = max(0.0, tot - paid)
        if due <= 0:
            continue
        last_pay = max((p.date for p in s.payments), default=None)
        days_ago = (today - last_pay).days if last_pay else 9999
        if due > 5000 and days_ago > 60:
            high_risk += 1
        elif due > 0 and days_ago > 30:
            med_risk += 1
        top_dues.append((due, s.name, s.student_class))

    top_dues.sort(reverse=True)
    top_3 = [{"name": n, "class": c, "due": round(d)} for d, n, c in top_dues[:3]]

    class_rates = []
    for (cls,) in db.query(models.Student.student_class).distinct().all():
        studs = db.query(models.Student).filter(
            models.Student.student_class == cls, models.Student.status == "active").all()
        if not studs:
            continue
        cls_billed = sum(sum(f.total_fee for f in s.fees) + (s.last_year_dues or 0) for s in studs)
        cls_paid   = sum(sum(p.amount for p in s.payments) for s in studs)
        if cls_billed > 0:
            rate = round(cls_paid / cls_billed * 100, 1)
            class_rates.append({"class": cls, "rate": rate, "due": round(max(0, cls_billed - cls_paid))})
    class_rates.sort(key=lambda r: r["rate"])

    return {
        "date": today.isoformat(),
        "students": {"total": total_students, "active": active_students},
        "fees": {
            "total_billed": round(total_fee_billed + last_yr_dues),
            "total_collected": round(total_collected),
            "total_due": round(total_due),
            "collection_rate_pct": round(total_collected / max(1, total_fee_billed + last_yr_dues) * 100, 1),
        },
        "expenses": {
            "total": round(total_expense),
            "this_month": round(expense_month),
            "prev_month": round(expense_prev),
            "by_category": expense_by_category,
        },
        "collections": {
            "this_month": round(collected_month),
            "prev_month": round(collected_prev),
        },
        "at_risk": {
            "high_risk_students": high_risk,
            "medium_risk_students": med_risk,
            "top_3_dues": top_3,
        },
        "class_collection_rates": class_rates,
        "net": round(total_collected - total_expense),
    }


def _call_claude(snapshot: dict) -> list[dict]:
    if not ANTHROPIC_KEY:
        return []
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2000,
        "system": ANALYSIS_PROMPT,
        "messages": [{"role": "user", "content": json.dumps(snapshot, indent=2)}],
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
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read())
        text = data["content"][0]["text"].strip()
        return json.loads(text)
    except Exception as e:
        print(f"[insights] claude error: {e}")
        return []


def generate_insights(db: Session) -> list[models.AIInsight]:
    """Generate fresh insights and persist. Called by scanner + on-demand."""
    snapshot = _build_snapshot(db)
    raw = _call_claude(snapshot)

    db.query(models.AIInsight).filter(
        models.AIInsight.dismissed == False
    ).update({"dismissed": True})

    saved = []
    for item in raw:
        row = models.AIInsight(
            category=item.get("category", "operations"),
            severity=item.get("severity", "info"),
            title=str(item.get("title", ""))[:200],
            body=item.get("body", ""),
            action_hint=item.get("action_hint"),
            generated_at=datetime.utcnow(),
            dismissed=False,
        )
        db.add(row)
        saved.append(row)
    db.commit()
    for r in saved:
        db.refresh(r)
    return saved


@router.get("", response_model=list[schemas.AIInsightOut])
def list_insights(
    include_dismissed: bool = False,
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    q = db.query(models.AIInsight)
    if not include_dismissed:
        q = q.filter(models.AIInsight.dismissed == False)
    return q.order_by(models.AIInsight.generated_at.desc()).limit(20).all()


@router.post("/generate", response_model=list[schemas.AIInsightOut])
def trigger_generation(
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    if not ANTHROPIC_KEY:
        raise HTTPException(503, "ANTHROPIC_API_KEY not configured.")
    return generate_insights(db)


@router.patch("/{insight_id}/dismiss")
def dismiss_insight(
    insight_id: int,
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    row = db.query(models.AIInsight).filter(models.AIInsight.id == insight_id).first()
    if not row:
        raise HTTPException(404, "Insight not found")
    row.dismissed = True
    db.commit()
    return {"ok": True}


@router.get("/snapshot")
def get_snapshot(
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    return _build_snapshot(db)
