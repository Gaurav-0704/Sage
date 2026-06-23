# Sage — Claude Code Work Order

> **How to run:** In Claude Code, type:
> `Read CLAUDE_CODE_PROMPT.md and execute it step by step.`

You are working in the **Sage** repo: a FastAPI + SQLAlchemy backend with an
agent-per-domain layout under `backend/agents/`, and a Create-React-App React 19
frontend under `frontend/src/`. Work through the steps **in order**. Ask me
before starting each TIER. Do not commit secrets.

---

## STEP 0 — Git hygiene (do first)
- A remote git origin is (or will be) attached. Confirm `git remote -v`.
- Ensure `.gitignore` covers: `backend/school.db`, `__pycache__/`,
  `*.pyc`, `frontend/node_modules/`, `frontend/build/`, `.env`, `*.env`.
- If `school.db` or `node_modules` are already tracked, `git rm --cached` them.
- **Commit + push at regular checkpoints**: after STEP 1, and after each TIER /
  STEP completes. Use clear messages (e.g. `feat: attendance module`,
  `chore: deploy config`). Never push secrets or the local DB.

## STEP 1 — Full scrape & verification (read-only, report before changing anything)
- Recursively read **every** source file:
  - backend: all `agents/*.py`, `database.py`, `models.py`, `schemas.py`,
    `auth.py`, `dependencies.py`, `audit_middleware.py`, `main.py`,
    `requirements.txt`.
  - frontend: every file in `src/` — all `pages/`, all `components/`,
    `auth.js`, `api.js`, and **all CSS**.
- Produce a verification report covering:
  - Every ORM model + every API route (method + path + role guard).
  - Every frontend route/page and which role sees it.
  - The exact CSS/responsive approach currently used (so we know how far the UI
    is from mobile-first).
  - A confirmed gap list vs. the target features below.
- Commit the report as `VERIFICATION_REPORT.md`, then push.

---

## STEP 2 — Excel sync + manual entry (NEW — highest priority this round)
Goal: students' and teachers' data stays synced between an Excel sheet and the
app, and can be created/edited manually from the interface — both paths write to
the same database so everything stays consistent.

**Backend**
- Excel **import**: endpoint(s) to upload `.xlsx`/`.csv` for students and for
  teachers. Parse with `openpyxl`/`pandas`. **Upsert** by a stable key
  (students: `admission_no`; teachers: `employee_id`) — update existing rows,
  insert new ones, report skipped/invalid rows. Never silently duplicate.
- Excel **export**: endpoint(s) to download the *current* students and teachers
  as `.xlsx` with the **exact same column layout** as the import template, so the
  user can "copy the existing Excel sheet for complete details" round-trip.
- Provide a downloadable **template** `.xlsx` for each (correct headers, one
  sample row).
- Validate on import: required fields, date formats, duplicate keys within the
  file, class/section sanity. Return a structured summary
  (`created`, `updated`, `skipped`, `errors[]`).
- Log every import to the existing audit log.

**Frontend**
- On the Students and Teachers pages (owner; staff for students):
  - "Add new" form to manually enter a student / teacher — same fields as the
    Excel columns, writing to the same models so data stays synced.
  - "Import from Excel" (upload + show the created/updated/skipped/errors
    summary) and "Download Excel" + "Download template" buttons.
- Manual entry and Excel import must hit the **same create/upsert logic** (no
  divergent code paths). Editing a record in the UI must reflect in the next
  export, and importing must reflect in the UI immediately.

Commit + push when STEP 2 is done and tested.

---

## STEP 3 — Core SMS features (ask before each tier)
**TIER 1 (non-negotiable for an SMS):**
- (a) **Attendance** — daily + period-wise student attendance; teachers mark,
  owner/parent/student view. Model: `Attendance(student_id, date, period,
  status, marked_by)`.
- (b) **Timetable** — classes/sections/periods/teachers/rooms with conflict
  detection; teacher + student views.
- (c) **Parent role** — add a `parent` role + parent↔student link; parent portal
  showing their child's attendance, marks, fees, assignments, notices.
- (d) **Real notifications** — wire the existing `Notification` model to an actual
  sender: email (SMTP/Resend env keys) + web push. Currently stored but never
  sent.

**TIER 2 (expected, high value):**
- Report-card / PDF generation (marks → graded report card).
- Assignment submission + grading flow (student uploads → teacher grades → marks).
- Online fee payment (Razorpay, ₹/en-IN formatting matches existing `fmtINR`).
- Announcements / notice board (broadcast, filterable by class/role).

Commit + push after each tier.

---

## STEP 4 — Mobile + web (Responsive + PWA)
- Refactor frontend CSS to **mobile-first responsive** (breakpoints, flexible
  flex/grid layouts, touch-sized targets; no fixed pixel widths that break on
  phones).
- Add **PWA** support: `manifest.json` + service worker → installable, offline
  app shell, push notifications.
Commit + push when done.

---

## STEP 5 — Railway deploy readiness (two services + Postgres)
- Replace hardcoded `http://127.0.0.1:8000` in `api.js` with
  `REACT_APP_API_BASE` (build-time env).
- Make CORS origins env-driven in `main.py` (`ALLOWED_ORIGINS`).
- **Migrate SQLite → Postgres**: SQLAlchemy URL from `DATABASE_URL`; keep SQLite
  fallback for local dev. Add **Alembic** migrations (do not drop data).
- Backend service: `railway.json`/`Procfile` →
  `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- Frontend service: static build (`npm run build`) deploy config; inject
  `REACT_APP_API_BASE` = backend public URL.
- Add `.env.example` documenting: `ANTHROPIC_API_KEY`, `DATABASE_URL`,
  JWT secret, SMTP/Resend keys, Razorpay keys, `REACT_APP_API_BASE`,
  `ALLOWED_ORIGINS`.
- Write `DEPLOY.md`: exact Railway steps for two services + Postgres plugin.
Commit + push when done.

---

## Constraints
- Keep the agent-per-domain backend pattern.
- Add migrations rather than dropping data.
- Manual entry and Excel import share one code path (single source of truth).
- Write tests for every new endpoint.
- Commit + push at every checkpoint; never commit secrets or `school.db`.
