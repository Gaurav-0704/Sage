"""
Scanner Agent — v0.6.

Runs a daily health scan over all agents and the database. Reports any
issues to Owner notifications. Scheduled at 02:00 local time on app
startup; Owner can also trigger on-demand.

The scan is intentionally simple and trustworthy: import each agent
module, run a sanity SELECT against each table, and (if `ruff` is
installed) run a quick lint over agent source files.
"""

import asyncio
import importlib
import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import notifications
import schemas
from database import SessionLocal
from dependencies import get_db, require_owner

router = APIRouter(prefix="/scanner", tags=["scanner"])

AGENT_NAMES = [
    "auth_agent", "students_agent", "fees_agent", "finance_agent",
    "expenses_agent", "reports_agent", "tiles_agent", "exams_agent",
    "teachers_agent", "assignments_agent",
    "teacher_self_agent", "student_self_agent",
    "audit_agent", "scanner_agent", "insights_agent",
]

TABLES = [
    ("users",          models.User),
    ("students",       models.Student),
    ("teachers",       models.Teacher),
    ("assignments",    models.Assignment),
    ("fee_structures", models.FeeStructure),
    ("fees",           models.Fee),
    ("payments",       models.Payment),
    ("expenses",       models.Expense),
    ("accounts",       models.Account),
    ("exams",          models.Exam),
    ("marks",          models.Mark),
    ("tiles",          models.Tile),
    ("audit_logs",     models.AuditLog),
    ("notifications",  models.Notification),
]


# ----------- Scan implementation ----------- #

def _import_check() -> list[dict]:
    findings = []
    for name in AGENT_NAMES:
        try:
            importlib.import_module(f"agents.{name}")
        except Exception as e:
            findings.append({"severity": "error", "category": "import",
                             "where": f"agents/{name}.py",
                             "detail": f"{type(e).__name__}: {e}"})
    return findings


def _db_check(db: Session) -> list[dict]:
    findings = []
    for name, model in TABLES:
        try:
            db.query(model).limit(1).all()
        except Exception as e:
            findings.append({"severity": "error", "category": "database",
                             "where": name,
                             "detail": f"{type(e).__name__}: {e}"})
    return findings


def _ruff_check() -> list[dict]:
    """Optional — only runs if ruff is installed."""
    findings = []
    backend_dir = Path(__file__).resolve().parent.parent
    try:
        out = subprocess.run(
            [sys.executable, "-m", "ruff", "check", str(backend_dir),
             "--output-format=json", "--quiet"],
            capture_output=True, text=True, timeout=30,
        )
        if out.stdout.strip():
            try:
                data = json.loads(out.stdout)
            except json.JSONDecodeError:
                data = []
            for d in data[:50]:
                findings.append({
                    "severity": "warning", "category": "lint",
                    "where": os.path.relpath(d.get("filename", "?"), backend_dir.parent),
                    "detail": f"{d.get('code', 'RUF')} · {d.get('message', '')}",
                })
    except FileNotFoundError:
        # ruff not installed — silently skip
        pass
    except Exception:
        pass
    return findings


def run_scan(db: Session, triggered_by: str = "manual") -> models.ScannerRun:
    run = models.ScannerRun(triggered_by=triggered_by, status="running")
    db.add(run); db.commit(); db.refresh(run)

    findings: list[dict] = []
    findings += _import_check()
    findings += _db_check(db)
    findings += _ruff_check()

    errors = sum(1 for f in findings if f["severity"] == "error")
    warns  = sum(1 for f in findings if f["severity"] == "warning")
    status = "ok" if not findings else ("issues" if errors == 0 else "failed")

    run.findings    = json.dumps(findings)
    run.issues_count = len(findings)
    run.finished_at = datetime.utcnow()
    run.status      = status
    run.summary     = (
        f"All clear ✓" if status == "ok"
        else f"{errors} error(s), {warns} warning(s)"
    )
    db.commit(); db.refresh(run)

    # Notify all owners.
    body_lines = [
        f"Scan triggered: {triggered_by}",
        f"Started:  {run.started_at:%Y-%m-%d %H:%M:%S} UTC",
        f"Finished: {run.finished_at:%Y-%m-%d %H:%M:%S} UTC",
        f"Result:   {run.summary}",
        "",
    ]
    if findings:
        body_lines.append("Top findings:")
        for f in findings[:10]:
            body_lines.append(f"  [{f['severity']}] {f['category']} · {f['where']} — {f['detail']}")
        if len(findings) > 10:
            body_lines.append(f"  … +{len(findings) - 10} more (see Scanner page)")
    body = "\n".join(body_lines)

    owners = db.query(models.User).filter(
        models.User.role == "owner", models.User.status == "active"
    ).all()
    subject = f"Scanner: {run.summary}"
    for ow in owners:
        notifications.send(db, ow.email, subject, body, kind="scanner")

    # Regenerate AI insights after every scan so the dashboard stays fresh
    try:
        from agents.insights_agent import generate_insights
        generate_insights(db)
    except Exception as e:
        print(f"[scanner] insights generation failed: {e}", file=sys.stderr)

    return run


# ----------- Scheduler ----------- #

async def scheduler_loop():
    """Sleeps until next 02:00 local time and runs a scan, in a loop."""
    while True:
        try:
            now = datetime.now()
            target = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            sleep_secs = (target - now).total_seconds()
            await asyncio.sleep(sleep_secs)
            db = SessionLocal()
            try:
                run_scan(db, triggered_by="schedule")
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[scanner] loop error: {e}", file=sys.stderr)
            # Sleep an hour before retrying so we don't spin
            await asyncio.sleep(3600)


# ----------- Routes ----------- #

@router.post("/run", response_model=schemas.ScannerRunOut)
def run_now(db: Session = Depends(get_db),
            _owner: models.User = Depends(require_owner)):
    return run_scan(db, triggered_by="manual")


@router.get("/runs", response_model=list[schemas.ScannerRunOut])
def list_runs(limit: int = 30,
              db: Session = Depends(get_db),
              _owner: models.User = Depends(require_owner)):
    return db.query(models.ScannerRun) \
        .order_by(models.ScannerRun.id.desc()).limit(limit).all()


@router.get("/runs/{run_id}", response_model=schemas.ScannerRunOut)
def get_run(run_id: int,
            db: Session = Depends(get_db),
            _owner: models.User = Depends(require_owner)):
    r = db.query(models.ScannerRun).filter(models.ScannerRun.id == run_id).first()
    if not r:
        raise HTTPException(404, "Run not found")
    return r
