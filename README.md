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

## What makes it different

### 1. Human-in-the-loop AI Assistant
Ask in plain English — "add a student named Riya in class 5" or "who owes more than ₹20,000?". Claude proposes exact, named actions. Each appears as a reviewable card; you can skip individual ones, edit parameters inline, or apply all. Destructive actions get an extra confirmation.

### 2. Proactive AI Insights
Every night at 2 AM (and on demand), I analyse school data and surface specific, actionable observations:
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
│   ├── agents/               # 17 domain agents (each = one FastAPI router)
│   ├── tests/                # pytest suite — financial logic + risk scoring
│   ├── main.py               # mounts all agents + middleware
│   ├── models.py             # SQLAlchemy ORM
│   ├── schemas.py            # Pydantic I/O schemas
│   ├── auth.py               # JWT + bcrypt
│   ├── seed_500.py           # 500-student realistic dataset
│   └── audit_middleware.py
├── frontend/
│   └── src/
│       ├── pages/            # One file per route
│       └── components/
├── run.py                    # One-line launcher (starts both servers)
├── docker-compose.yml
└── .env.example
```

---

## License

MIT — see [LICENSE](LICENSE).
