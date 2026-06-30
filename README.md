# Sage — AI-First School ERP

**A complete school management system for K–10, built around an AI assistant that proposes changes and waits for the owner's approval before anything runs.**

Most school software is a database with forms on top. Sage keeps the full operational core every school needs — students, attendance, timetable, fees, exams, a parent portal — and adds an AI layer the others don't: an assistant you direct in plain English, proactive nightly insights, and a complete audit trail of every change. It is self-hosted, MIT-licensed, and yours to run.

---

## ▶ Try it live

**[https://sageai.up.railway.app](https://sageai.up.railway.app)** — a running instance you can sign into right now.

```
Owner   owner@sage.school / owner123
Staff   staff@sage.school / staff123
```

Sign in as the **Owner** to see the full system; explore the dashboard, add a student, mark attendance, build a timetable, or ask the AI assistant to do it for you.

---

## Why Sage is different

Tools like Fedena, Gibbon, OpenSIS and Teachmint cover the standard ground. Sage covers that **same core** and adds three things they generally don't — an AI co-pilot, proactive insight, and full accountability.

| | Typical school apps | **Sage** |
|---|:---:|:---:|
| Attendance · timetable · fees · marks · parent portal | ✅ | ✅ |
| Excel ↔ app two-way sync (one shared save path) | ⚠️ import-only | ✅ |
| AI assistant that **proposes** actions and waits for approval | ❌ | ✅ |
| Proactive nightly insights (dues, risk, expense spikes) | ❌ | ✅ |
| Full, searchable audit trail of every change | partial | ✅ |
| Self-hosted · no per-seat licensing · MIT | rare | ✅ |

The three pillars that set it apart:

- **Human-in-the-loop AI assistant.** Ask in plain English — *"add a student named Riya in class 5"* or *"who owes more than ₹20,000?"*. Claude proposes exact, named actions as reviewable cards. Nothing executes until the owner approves it; destructive actions need an extra confirmation. The AI is a co-pilot, never an autopilot.
- **Proactive insights.** Every night (and on demand) Sage analyses the school's data and surfaces specific, actionable observations — students with high dues and no recent payment, expense spikes versus prior months, fee-collection rate by class, at-risk students approaching exams — plus a transparent, rule-based fee-risk score (no black-box ML).
- **Total accountability.** Every state-changing action is automatically logged with who, what, when and from which IP — searchable and filterable, in table or timeline view. A nightly self-diagnostic agent checks database health and re-imports every module, reporting issues to the owner.

> The honest version: if you only need a records-and-fees register, many tools do that. Sage is for someone who wants that **plus** an AI co-pilot and a transparent system they own outright. Multi-school SaaS tenancy, library, transport GPS and payroll are intentionally out of scope.

---

## What's inside

A full K–10 system, not a demo:

- **Students & teachers** — records, roster, and two-way **Excel/CSV** sync (import, export, template) that shares the *exact same save path* as the manual "Add" form, so the sheet and the app never drift apart.
- **Attendance** — daily *and* period-wise; teachers mark their classes, owners/parents/students view.
- **Timetable** — weekly class schedule with **conflict detection** (no double-booked teacher, no clashing slot).
- **Fees** — structures, bills, payments, printable receipts, and **online payment via Razorpay** (₹/en-IN), settling against dues automatically.
- **Exams & marks** — gradebook plus a generated **report-card PDF** per student.
- **Assignments** — teacher posts → student submits (text + file) → teacher grades with feedback.
- **Parent portal** — parents self-sign-up and **claim their child** (verified, owner-approved), then view that child's attendance, marks, fees and assignments, and pay online.
- **Notice board** — announcements targeted by role and class.
- **Notifications** — real email via Resend or SMTP on fee payments and published results.
- **Money** — live cash/bank balances, daily / monthly / yearly reports, expense tracking.
- **Five roles** — owner, staff, teacher, student, parent — each with tailored views.
- **Mobile-ready** — mobile-first responsive UI, installable as a **PWA** with an offline app shell.

---

## Quality & verification

Sage isn't a prototype — every domain is covered by automated tests and the full stack has been verified end-to-end.

- **86 backend tests pass** (`pytest`), covering the logic that would actually hurt a school if wrong: fee math and due settlement, payment recording, attendance upsert/percentage, timetable conflict detection, parent claim verification, Excel import upsert/dedupe, report-card scoring, Razorpay signature verification, announcement targeting, and the demo seeder.
- **Frontend builds clean** (`react-scripts build`, 0 errors) and lints clean.
- **151 API routes** mount and import without error.
- **Database-portable** — runs on SQLite (dev) and PostgreSQL (prod); schema is versioned with **Alembic** and verified to migrate from empty on both engines.
- **Live end-to-end smoke** (single-service, clean database): the SPA serves, all five roles sign in, and every major surface — dashboard, finance, monthly/daily reports, insights, students, attendance, timetable, announcements, settings, report-card PDF — returns `200` with correct values.
- **Clean repository** — no secrets, keys, debug logging or stray files committed; databases, `.env` and uploads are git-ignored.

```bash
cd backend && pytest -q        # 86 passed
```

---

## Getting started

After cloning, one command runs the whole stack. Pick whichever fits your machine.

```bash
git clone https://github.com/Gaurav-0704/Sage.git
cd Sage
```

**Docker — only Docker required, nothing else to install:**

```bash
docker compose up --build
# UI → http://localhost:3000      API → http://localhost:8000/api
# Sample data?  SEED_DEMO=true docker compose up --build
```

**Without Docker — needs Python 3.11+ and Node 18+:**

```bash
python run.py        # creates a venv, installs all deps, starts both servers
```

Sign in with `owner@sage.school` / `owner123`, then change the password in **Settings** and set your school details. The AI assistant is optional — add `ANTHROPIC_API_KEY` to `.env` (`cp .env.example .env`) to enable it; everything else works with zero keys.

Deploying to the cloud (single service + Postgres on Railway) is documented in **[DEPLOY.md](DEPLOY.md)**.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python · FastAPI · SQLAlchemy · SQLite (dev) / PostgreSQL (prod) · Alembic |
| Frontend | React 19 · Recharts · Axios · PWA (installable + offline shell) |
| AI | Anthropic Claude API (tool use + SSE streaming) |
| Auth | JWT · bcrypt · roles: owner / staff / teacher / student / parent |
| Infra | Docker · docker-compose · Railway |

---

## Architecture

The backend is organised as **21+ domain agents**, each a self-contained FastAPI router mounted under `/api`:

```
auth · students · fees · finance · expenses · reports · tiles · exams
teachers · assignments · teacher_self · student_self · audit · scanner
ai · records · insights · attendance · timetable · parents · announcements · config
```

`AuditMiddleware` intercepts every mutating request and writes a human-readable log entry. The scanner agent schedules itself at startup via `asyncio`. The AI agent uses Claude's tool-use API and **never executes tools directly** — it returns proposed tool calls as JSON, and `/api/ai/execute` runs only the owner-approved subset.

```
Sage/
├── backend/
│   ├── agents/            # 21+ domain agents (each = one FastAPI router)
│   ├── migrations/        # Alembic schema migrations
│   ├── tests/             # pytest suite (86 tests)
│   ├── main.py            # mounts agents under /api + serves the React build
│   ├── models.py          # SQLAlchemy ORM
│   ├── excel_io.py        # .xlsx/.csv import + export
│   ├── report_cards.py    # report-card PDF (fpdf2)
│   ├── razorpay_client.py # online payments
│   └── notifications.py   # email (Resend / SMTP)
├── frontend/src/          # React app (pages/ + components/)
├── run.py                 # one-command launcher
├── Dockerfile             # single-service image (API + built UI)
└── docker-compose.yml
```

---

## License

© 2026 **Gaurav Singh Thakur**. Released under the MIT License — see [LICENSE](LICENSE).
