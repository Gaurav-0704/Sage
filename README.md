# Sage — AI-First School ERP

> A school management system where the owner directs an AI assistant that **proposes** changes and **waits for approval** before anything runs.

Sage is not a CRUD app with a chatbot bolted on. Claude is the primary interface for the owner — it reads school data, surfaces proactive nightly insights, and proposes precise actions. Nothing executes until the owner reviews and approves each one individually.

---

## Quick start

Pick one — both are a single command after cloning.

```bash
git clone https://github.com/Gaurav-0704/Sage.git
cd Sage
```

**Option A — Docker (only Docker needed, nothing else to install):**

```bash
docker compose up --build
# UI → http://localhost:3000      API → http://localhost:8000/api
# Want sample data?  SEED_DEMO=true docker compose up --build
```

**Option B — no Docker (needs Python 3.11+ and Node 18+):**

```bash
python run.py               # creates a venv, installs backend + frontend deps, starts both
# UI → http://localhost:3000      API → http://localhost:8000/api  ·  /docs for Swagger
```

Sign in with the seeded owner account, then change the password in **Settings**:

- Owner: `owner@sage.school` / `owner123`
- Staff: `staff@sage.school` / `staff123`

The AI assistant is optional — add `ANTHROPIC_API_KEY` to `.env` (`cp .env.example .env`) to enable it. Everything else works without any keys.

```bash
python run.py --setup       # install deps only, don't start
python run.py --backend     # API only
python run.py --frontend    # UI only
```

**Deploy to the cloud:** one-click-ish on Railway (single service + Postgres) — see [DEPLOY.md](DEPLOY.md).

---

## What's inside

A complete K–10 school system, not a demo:

- **Students & teachers** — records, roster, and two-way **Excel/CSV** sync (import, export, template) that shares the exact same save path as the manual "Add" form, so the sheet and the app never drift apart.
- **Attendance** — daily *and* period-wise; teachers mark their classes, owners/parents/students view.
- **Timetable** — weekly class schedule with **conflict detection** (no double-booked teacher, no clashing slot).
- **Fees** — fee structures, bills, payments, printable receipts, and **online payment via Razorpay** (₹/en-IN), all settling against dues automatically.
- **Exams & marks** — gradebook plus a generated **report-card PDF** per student.
- **Assignments** — teacher posts → student submits (text + file upload) → teacher grades with feedback.
- **Parent portal** — parents self-sign-up and **claim their child** (verified, owner-approved), then see that child's attendance, marks, fees and assignments — and can pay online.
- **Notice board** — announcements targeted by role and class.
- **Real notifications** — email via Resend or SMTP, sent on fee payments and published results.
- **Money** — live cash/bank balances, daily / monthly / yearly reports, expense tracking.
- **Five roles** — owner, staff, teacher, student, parent — each with its own tailored views.
- **Works on phones** — mobile-first responsive UI, installable as a **PWA** with an offline app shell.

…on top of the AI and accountability layer below, which is what actually sets it apart.

---

## What makes it different

### 1. Human-in-the-loop AI Assistant
Ask in plain English — "add a student named Riya in class 5" or "who owes more than ₹20,000?". Claude proposes exact, named actions. Each appears as a reviewable card; you can skip individual ones, edit parameters inline, or apply all. Destructive actions get an extra confirmation.

### 2. Proactive AI Insights
Every night at 2 AM (and on demand), Sage analyses school data and surfaces specific, actionable observations:
- Students with high dues and no payment in 60+ days
- Expense spikes vs prior months
- Fee collection rate by class
- At-risk students approaching board exams

### 3. Fee Risk Scoring
Rule-based scoring — `min(50, due/1000) + min(50, days_since/6)` — surfaces the highest-risk students on the dashboard before they become a collection problem. No fake ML, transparent formula.

### 4. Full Audit Trail
Every state-changing action (POST, PUT, DELETE, PATCH) is automatically logged with who, what, when, and from which IP. Searchable by keyword, filterable by actor, method, and time window. Two views: table and timeline.

### 5. Nightly Self-Diagnostics
A scanner agent checks DB health, imports all agent modules, and optionally runs `ruff` lint. Findings are sent as owner notifications. On-demand runs available.

---

## How Sage compares to other school apps

Tools like Fedena, Gibbon, OpenSIS or Teachmint cover the standard ground — records, attendance, fees, timetable, a parent portal. Sage covers that **same core**, and adds three things they generally don't:

| | Typical school apps | Sage |
|---|---|---|
| Attendance · timetable · fees · marks · parent portal | ✅ | ✅ |
| AI assistant that *proposes* actions and waits for approval | ❌ | ✅ |
| Proactive nightly insights (dues, risk, expense spikes) | ❌ | ✅ |
| Full, searchable audit trail of every change | partial | ✅ |
| Excel ↔ app two-way sync sharing one save path | ⚠️ import-only | ✅ |
| Self-hosted, no per-seat licensing, MIT-licensed | rare | ✅ |

The honest version: if you only need a records-and-fees register, plenty of tools do that. Sage is for someone who wants that **plus** an AI co-pilot and a transparent, auditable system they own outright. It's not multi-school/SaaS tenancy, and a few extras (library, transport GPS, payroll) are intentionally out of scope.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · FastAPI · SQLAlchemy · SQLite (dev) / Postgres (prod) · Alembic |
| Frontend | React 19 · Recharts · Axios · PWA (installable + offline shell) |
| AI | Anthropic Claude API (tool use + SSE streaming) |
| Auth | JWT · bcrypt · roles: owner / staff / teacher / student / parent |
| Infra | Docker · docker-compose · Railway |

---

## Running tests

```bash
cd backend
pytest -q                   # 86 tests — fees, payments, attendance, timetable,
                            # parents, Excel sync, report cards, Razorpay, more
```

---

## Docker

```bash
cp .env.example .env        # add your ANTHROPIC_API_KEY
docker compose up --build
```

---

## Architecture

The backend has **21+ agents**, each owning one domain:

```
auth · students · fees · finance · expenses · reports
tiles · exams · teachers · assignments
teacher_self · student_self
audit · scanner · ai · records · insights
attendance · timetable · parents · announcements · config
```

Each agent is a self-contained FastAPI router mounted in `main.py`. `AuditMiddleware` intercepts every mutating request and writes a human-readable log entry. The `ScannerAgent` schedules itself at startup using `asyncio`.

The AI agent uses Claude's tool-use API — it never executes tools directly. It returns proposed tool calls as JSON; `/ai/execute` runs only the owner-approved subset.

---

## Project structure

```
Sage/
├── backend/
│   ├── agents/               # 21+ domain agents (each = one FastAPI router)
│   ├── migrations/           # Alembic schema migrations
│   ├── tests/                # pytest suite (86 tests)
│   ├── main.py               # mounts agents under /api + serves the React build
│   ├── models.py             # SQLAlchemy ORM
│   ├── schemas.py            # Pydantic I/O schemas
│   ├── auth.py               # JWT + bcrypt
│   ├── notifications.py      # email (Resend / SMTP)
│   ├── excel_io.py           # .xlsx/.csv import + export
│   ├── report_cards.py       # report-card PDF (fpdf2)
│   ├── razorpay_client.py    # online payments
│   ├── demo_seed.py          # optional sample data (SEED_DEMO=true)
│   └── audit_middleware.py
├── frontend/
│   └── src/
│       ├── pages/            # one file per route
│       └── components/
├── run.py                    # one-command launcher (starts both servers)
├── Dockerfile                # single-service image (API + built UI)
├── docker-compose.yml
└── .env.example
```

---

## License

© 2026 Gaurav Singh Thakur. Released under the MIT License — see [LICENSE](LICENSE).
