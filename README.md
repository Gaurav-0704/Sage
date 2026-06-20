# Sage — AI-Powered School ERP

> A school management system where the admin controls an AI assistant that **proposes** changes and **waits for human approval** before anything runs.

Sage is not a CRUD app with a chatbot bolted on. The AI assistant is the primary interface for the owner — it reads school data, surfaces proactive insights, and proposes precise actions. Nothing executes until the owner reviews and approves each one individually.

---

## What makes it different

### 1. Human-in-the-loop AI Assistant
Ask in plain English. Claude proposes exact actions (create student, record payment, apply fee structure). Each action is shown as a reviewable card — you can skip individual ones, edit the parameters inline, or apply all. Destructive actions require an extra confirmation.

### 2. Proactive AI Insights
Every night at 2 AM (and on demand), the system analyses school data and surfaces specific, actionable observations:
- Students with high dues and no payment in 60+ days
- Expense spikes vs prior months
- Fee collection rate by class
- At-risk students before board exams

### 3. Full Audit Trail
Every state-changing action (POST, PUT, DELETE, PATCH) is automatically logged — who did it, what changed, when, from which IP. Searchable and filterable.

### 4. Nightly Self-Diagnostics
A scanner agent checks DB health, imports all agent modules, and optionally runs `ruff` lint at 2 AM. Findings are sent to the owner as notifications. On-demand runs available.

### 5. Fee Risk Scoring
Rule-based at-risk detection — students with dues above threshold and no recent payment surface on the dashboard with a risk score. No fake ML, real operational value.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · FastAPI · SQLAlchemy · SQLite |
| Frontend | React · Recharts · Axios |
| AI | Anthropic Claude API (tool use + streaming) |
| Auth | JWT · bcrypt |
| Infra | Docker Compose |

---

## Run locally

### Prerequisites
- Python 3.11+
- Node 18+
- An [Anthropic API key](https://console.anthropic.com)

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env    # add your ANTHROPIC_API_KEY
uvicorn main:app --reload
```

Backend runs at http://localhost:8000. Default credentials:
- Owner: `owner@nagarjuna.school` / `owner123`
- Staff: `staff@nagarjuna.school` / `staff123`

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

Frontend runs at http://localhost:3000.

### 3. Or use Docker Compose

```bash
cp .env.example .env   # add your ANTHROPIC_API_KEY
docker compose up --build
```

---

## Architecture

The backend is decomposed into **16 agents**, each owning one domain:

```
auth · students · fees · finance · expenses · reports
tiles · exams · teachers · assignments
teacher_self · student_self
audit · scanner · ai · records
```

Each agent is a self-contained FastAPI router mounted in `main.py`. The `AuditMiddleware` intercepts every mutating request and writes a human-readable log entry. The `ScannerAgent` schedules itself with `asyncio` on startup.

The AI agent uses Claude's **tool use** API — it never executes tools directly. It returns proposed tool calls as JSON; the `/ai/execute` endpoint runs only the owner-approved subset.

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Project structure

```
sage/
├── backend/
│   ├── agents/          # 16 domain agents (each = one FastAPI router)
│   ├── tests/           # pytest suite — financial logic + smoke tests
│   ├── main.py          # mounts all agents + middleware
│   ├── models.py        # SQLAlchemy ORM
│   ├── schemas.py       # Pydantic I/O schemas
│   ├── auth.py          # JWT + bcrypt
│   └── audit_middleware.py
├── frontend/
│   └── src/
│       ├── pages/       # One file per route
│       └── components/
├── docker-compose.yml
└── .env.example
```
