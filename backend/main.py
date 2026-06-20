"""
Sage — FastAPI gateway.

I mount every agent, the audit middleware, CORS, and start the nightly
scanner. Each agent owns one domain and lives in its own file so I can
edit them independently without touching the others.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import models
import auth
from database import SessionLocal, engine, Base
from audit_middleware import AuditMiddleware

from agents import (
    auth_agent,
    students_agent,
    fees_agent,
    finance_agent,
    expenses_agent,
    reports_agent,
    tiles_agent,
    exams_agent,
    teachers_agent,
    assignments_agent,
    teacher_self_agent,
    student_self_agent,
    audit_agent,
    scanner_agent,
    ai_agent,
    records_agent,
    insights_agent,
)

SCHOOL_NAME = "Sage"
SCHOOL_SHORT = "SGE"

Base.metadata.create_all(bind=engine)


def _migrate():
    """Pick up new columns / tables added by newer versions without dropping data."""
    add_col = [
        ("users",    "status",                "VARCHAR DEFAULT 'active'"),
        ("users",    "can_do_front_office",   "BOOLEAN DEFAULT 0"),
        ("students", "user_id",               "INTEGER"),
        ("payments", "fee_head",              "VARCHAR"),
    ]
    with engine.connect() as conn:
        for table, col, decl in add_col:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {decl}"))
                conn.commit()
            except Exception:
                pass

        # Backfill teacher_classes join table from legacy classes_taught string
        try:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS teacher_classes "
                "(id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, student_class VARCHAR NOT NULL)"
            ))
            conn.commit()
            teachers = conn.execute(text("SELECT id, classes_taught FROM teachers")).fetchall()
            for tid, cls_str in teachers:
                if not cls_str:
                    continue
                existing = conn.execute(
                    text("SELECT 1 FROM teacher_classes WHERE teacher_id=:tid LIMIT 1"),
                    {"tid": tid}
                ).fetchone()
                if existing:
                    continue
                for cls in [c.strip() for c in cls_str.split(",") if c.strip()]:
                    conn.execute(
                        text("INSERT INTO teacher_classes (teacher_id, student_class) VALUES (:tid, :cls)"),
                        {"tid": tid, "cls": cls}
                    )
            conn.commit()
        except Exception:
            pass


DEFAULT_TILES = [
    {"label": "Tuition Fee",   "kind": "payment", "fee_head": "Tuition",
     "icon": "📚", "color": "#d4a574", "sort_order": 10},
    {"label": "Transport Fee", "kind": "payment", "fee_head": "Transport",
     "icon": "🚌", "color": "#a3d977", "sort_order": 20},
    {"label": "Books Fee",     "kind": "payment", "fee_head": "Books",
     "icon": "📖", "color": "#fbbf24", "sort_order": 30},
    {"label": "Uniform Fee",   "kind": "payment", "fee_head": "Uniform",
     "icon": "👕", "color": "#c89bf5", "sort_order": 40},
    {"label": "Other Fee",     "kind": "payment", "fee_head": "Other",
     "icon": "💰", "color": "#7dd3fc", "sort_order": 50},
    {"label": "Salary",        "kind": "expense", "category": "salary",
     "icon": "👨‍🏫", "color": "#f97362", "sort_order": 60},
    {"label": "Utilities",     "kind": "expense", "category": "utilities",
     "icon": "💡", "color": "#fb923c", "sort_order": 70},
    {"label": "Supplies",      "kind": "expense", "category": "supplies",
     "icon": "📦", "color": "#a78bfa", "sort_order": 80},
    {"label": "Maintenance",   "kind": "expense", "category": "maintenance",
     "icon": "🔧", "color": "#94a3b8", "sort_order": 90},
]


def seed_defaults():
    db = SessionLocal()
    try:
        if not db.query(models.User).filter(models.User.email == "owner@sage.school").first():
            db.add(models.User(
                name="School Owner", email="owner@sage.school",
                password=auth.hash_password("owner123"),
                role="owner", status="active",
            ))
        if not db.query(models.User).filter(models.User.email == "staff@sage.school").first():
            db.add(models.User(
                name="Front Office", email="staff@sage.school",
                password=auth.hash_password("staff123"),
                role="staff", status="active",
            ))
        for acct_name in ("cash", "bank"):
            if not db.query(models.Account).filter(models.Account.name == acct_name).first():
                db.add(models.Account(name=acct_name, opening_balance=0))
        if db.query(models.Tile).count() == 0:
            for t in DEFAULT_TILES:
                db.add(models.Tile(**t))
        db.commit()
    finally:
        db.close()


_scanner_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scanner_task
    _migrate()
    seed_defaults()
    _scanner_task = asyncio.create_task(scanner_agent.scheduler_loop())
    yield
    if _scanner_task:
        _scanner_task.cancel()


app = FastAPI(
    title="Sage — AI-first School ERP",
    description="AI-powered school management for K-10.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount every agent. Each owns one job:
#   auth         — sign in, sign up, password reset, user admin
#   students     — student records + roster + CSV import/export
#   fees         — fee structures + bills + payments + receipts
#   finance      — live cash + bank balances
#   expenses     — categorized school expenses
#   reports      — dashboard, daily/monthly/yearly summaries
#   tiles        — front-office quick-action tiles
#   exams        — exams + marks + per-student performance
#   teachers     — teacher records (Owner CRUD)
#   assignments  — assignments per class/subject (Teacher CRUD)
#   teacher_self — /teacher/me dashboard + view of own classes
#   student_self — /student/me dashboard + own marks/assignments
#   audit        — read-only view of the audit log
#   scanner      — nightly self-check + on-demand run
#   ai           — Owner-only assistant; proposes actions, never auto-applies
for r in (auth_agent.router, students_agent.router, fees_agent.router,
          finance_agent.router, expenses_agent.router, reports_agent.router,
          tiles_agent.router, exams_agent.router, teachers_agent.router,
          assignments_agent.router, teacher_self_agent.router,
          student_self_agent.router, audit_agent.router, scanner_agent.router,
          ai_agent.router, records_agent.router, insights_agent.router):
    app.include_router(r)


@app.get("/")
def health():
    return {
        "name": "Sage",
        "tagline": "AI-powered School ERP",
        "version": "1.0.0",
        "agents": [
            "auth", "students", "fees", "finance", "expenses",
            "reports", "tiles", "exams",
            "teachers", "assignments",
            "teacher_self", "student_self",
            "audit", "scanner", "ai", "records", "insights",
        ],
        "status": "ok",
    }
