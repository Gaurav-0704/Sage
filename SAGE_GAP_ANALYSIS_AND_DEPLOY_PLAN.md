# Sage — Gap Analysis vs. School Management Systems + Railway Deployment Plan

> Scope note: The Linux VM was unavailable, so this is based on reading the
> core source (backend `main.py`, `models.py`, all 17 agents referenced,
> frontend `App.js`, `api.js`, `package.json`, `requirements.txt`). A full
> file-by-file scrape is deferred to Claude Code via the prompt at the end.

---

## 1. What Sage is today (verified from source)

**Stack** [High Confidence]
- Backend: FastAPI 0.136 + SQLAlchemy 2.0 + **SQLite** (`school.db`), JWT auth (python-jose + bcrypt), agent-per-domain architecture (17 routers mounted in `main.py`).
- Frontend: **Create React App** (react-scripts 5) + React 19 + react-router 6 + axios + recharts.
- AI: Owner-only assistant via `ANTHROPIC_API_KEY` (propose-then-confirm, never auto-applies) + nightly scanner + nightly AI insights.

**Roles**: owner, staff, teacher, student (4 roles, RBAC via `RoleRoute`).

**Domains already covered** (from models + agents):
Students (+CSV import/export), Teachers, Assignments, Fees (structures/bills/payments/receipts), Expenses, Finance (cash/bank accounts), Exams + Marks, Reports/dashboards, Front-office Tiles, Audit log, Self-scanning agent, AI assistant, AI insights, Notifications (stored, `delivered` flag).

This is already a **competent fee-and-records ERP with an AI layer** — genuinely above average for a K-10 self-built system. The AI agent + audit + nightly scanner are differentiators most commercial SMS products don't have.

---

## 2. Comparison vs. mainstream SMS (Fedena, Gibbon, OpenSIS, Gradelink, Classe365, Teachmint, PowerSchool)

Industry "must-have" feature set for 2026 (per buyer guides): student records, **attendance**, gradebook/report cards, fee collection, **timetable**, **parent portal**, **communication (SMS/email/push)**, admissions, library, transport, HR/payroll, analytics.

| Feature | Sage today | Typical SMS | Gap |
|---|---|---|---|
| Student records + CSV | ✅ | ✅ | — |
| Fee collection + receipts | ✅ | ✅ | Add online payment gateway |
| Exams / marks | ✅ basic | ✅ | No report-card generation / grade scales |
| Expenses + accounts | ✅ | partial | Sage is *stronger* here |
| AI assistant / insights | ✅ | ❌ rare | Sage advantage |
| Audit log | ✅ | partial | Sage advantage |
| **Attendance (student & staff)** | ❌ **none** | ✅ core | **Critical gap** |
| **Timetable / scheduling** | ❌ none | ✅ core | **Critical gap** |
| **Parent role / portal** | ❌ (only student) | ✅ core | **Critical gap** |
| **Communication: real email/SMS/push** | ⚠️ stored only, not sent | ✅ core | **High** |
| Homework/assignment submission + grading | ⚠️ assignments exist, no submission flow | ✅ | Medium |
| Report cards (PDF) | ❌ | ✅ | Medium |
| Admissions/enquiry pipeline | ❌ | ✅ | Medium |
| Library | ❌ | common | Low |
| Transport tracking | ⚠️ transport *fee* only | common | Low |
| HR / payroll | ⚠️ salary as expense only | common | Low |
| Timetable-aware attendance / period log | ❌ | ✅ | Medium |
| Multi-school / multi-branch tenancy | ❌ single school | varies | Low (unless SaaS) |
| Mobile app / responsive | ⚠️ unknown CSS, no PWA | ✅ | **High (you asked for mobile)** |

### The honest verdict
The three things that make something *recognizably a school management system* rather than a *fee/records app* are **attendance, timetable, and a parent portal with real notifications**. Sage is missing all three. Everything else is polish.

---

## 3. Prioritized gap list (what to add to Sage)

**Tier 1 — non-negotiable to call it an SMS**
1. **Attendance** — daily + period-wise student attendance; teacher marks, owner/parent views; staff attendance optional. New models: `Attendance(student_id, date, period, status, marked_by)`.
2. **Timetable** — `Period`, `TimetableEntry(class, section, day, period, subject, teacher_id, room)`; teacher + student views; conflict detection.
3. **Parent role + portal** — add `parent` role; `parent_student` link table; parent sees their child's attendance, marks, fees, assignments, notices.
4. **Real notifications** — wire the existing `Notification` model to an actual sender: email (SMTP/Resend/SendGrid), and push (web-push/FCM). Currently stored but `delivered` never fires.

**Tier 2 — expected, high value**
5. Report-card / PDF generation (marks → graded report card; reuse the `pdf` skill server-side or a Python lib).
6. Assignment **submission + grading** flow (student uploads, teacher grades → feeds marks).
7. Online **fee payment gateway** (Razorpay for India given ₹/en-IN formatting; Stripe otherwise).
8. Announcements / notice board (broadcast, filterable by class/role).

**Tier 3 — nice to have**
9. Admissions enquiry pipeline. 10. Library. 11. Transport/route + GPS. 12. HR/payroll proper. 13. Multi-branch tenancy (only if going SaaS).

---

## 4. Web + mobile friendliness

You don't need a separate native app to be "mobile friendly." Recommended path, cheapest → richest:

1. **Responsive + PWA (recommended first)** [High Confidence on effort/value]
   - Audit/refactor CSS to mobile-first (flex/grid, breakpoints, no fixed widths), touch-sized targets.
   - Add `manifest.json` + service worker → installable PWA, offline shell, push notifications. CRA supports this with minimal setup.
   - Pros: one codebase, instant updates, installable on Android/iOS home screen. Cons: iOS push is limited (improving), no app-store presence.
2. **Capacitor wrapper (later, optional)** — wrap the same React build into iOS/Android app-store binaries with native push. Low extra cost if PWA is done first.
3. **React Native (avoid for now)** — full rewrite of UI; only justified if you need deep native features. Tradeoff: large time cost, second codebase to maintain. **I'd advise against it at this stage.**

> Caveat [Low Confidence]: I haven't read the CSS files, so I can't yet rate how far the current UI is from responsive. The Claude Code prompt below asks for that audit explicitly.

---

## 5. Railway deployment plan

**Key blockers to fix before deploy** [High Confidence]:
- `api.js` hardcodes `http://127.0.0.1:8000` → must become an env var (`REACT_APP_API_BASE` injected at build).
- CORS in `main.py` is hardcoded to `localhost:3000` → must read allowed origins from env.
- **SQLite is the biggest risk**: Railway's filesystem is ephemeral on redeploy. `school.db` will be **wiped on every deploy**. Either attach a Railway Volume (quick) or migrate to **Postgres** (correct). For a real school with real data, **migrate to Postgres** — SQLite + ephemeral disk = guaranteed data loss.
- Secrets: `ANTHROPIC_API_KEY`, JWT secret, SMTP/payment keys → Railway variables, never committed.

**Recommended topology**: two Railway services in one repo (monorepo with root dirs + watch paths):
- `backend/` service → `uvicorn main:app --host 0.0.0.0 --port $PORT`, `railway.json`/`Procfile`, `requirements.txt`. Add Postgres plugin.
- `frontend/` service → build static (`npm run build`) and serve (Railway static, or a tiny server). Set `REACT_APP_API_BASE` to the backend's public URL at build time.

**Tradeoffs**:
- *Two services*: clean separation, independent scaling, but two URLs + CORS config. (Recommended.)
- *Single service, FastAPI serves the React build*: one URL, no CORS, simpler/cheaper — but couples deploys and FastAPI serving static assets isn't ideal at scale. Fine for a single school. Good "v1" option.

---

## 6. Ready-to-paste prompt for Claude Code (full scrape + implement)

```
You are working in the Sage repo (FastAPI + SQLAlchemy/SQLite backend with an
agent-per-domain layout under backend/agents/, and a Create-React-App React 19
frontend under frontend/src/). 

STEP 1 — FULL SCRAPE & REPORT (read-only, do this first):
- Recursively read every source file in backend/ (all agents, database.py,
  schemas.py, auth.py, dependencies.py, audit_middleware.py) and frontend/src/
  (every page in pages/, every component, auth.js, api.js, all CSS).
- Produce an accurate inventory: every model, every API route (method+path+role
  guard), every frontend page/route, and the exact CSS/responsive approach used.
- Output a gap report confirming what exists vs. this target feature set.

STEP 2 — IMPLEMENT in priority order (ask me before each tier):
TIER 1: (a) Attendance (daily + period, teacher marks, owner/parent/student
views); (b) Timetable (classes/sections/periods/teachers, conflict detection,
teacher+student views); (c) a new `parent` role with parent↔student linking and
a parent portal (child's attendance, marks, fees, assignments, notices);
(d) wire the existing Notification model to a real sender (email via SMTP/Resend
env keys + web push).
TIER 2: report-card PDF generation; assignment submission+grading; online fee
payment (Razorpay, ₹/en-IN); announcements/notice board.

STEP 3 — MOBILE/WEB:
- Audit frontend CSS; refactor to mobile-first responsive (breakpoints, flexible
  layouts, touch targets). 
- Add PWA support (manifest.json + service worker, installable, offline shell,
  push notifications).

STEP 4 — RAILWAY DEPLOY READINESS:
- Replace hardcoded http://127.0.0.1:8000 in api.js with REACT_APP_API_BASE.
- Make CORS origins env-driven in main.py.
- Migrate from SQLite to Postgres (SQLAlchemy URL from DATABASE_URL env; keep a
  SQLite fallback for local dev). Provide an Alembic migration setup.
- Add railway.json (or Procfile) for the backend (uvicorn main:app --host
  0.0.0.0 --port $PORT) and a deploy config for the frontend static build.
- Add .env.example documenting ANTHROPIC_API_KEY, DATABASE_URL, JWT secret,
  SMTP/Razorpay keys, REACT_APP_API_BASE, ALLOWED_ORIGINS.
- Write a DEPLOY.md with exact Railway steps (two services + Postgres plugin).

Constraints: keep the agent-per-domain pattern; add migrations rather than
dropping data; do not commit secrets; write tests for new endpoints.
```

---

## Sources
- [School Management Software Buyer's Guide 2026 — OpenEduCat](https://openeducat.org/articles/school-management-software-buyers-guide/)
- [10 Features Every School Management Software Must Have 2026 — AppAcademia](https://myappacademia.com/blog/best-school-management-software.html)
- [Deploy a FastAPI App — Railway Guides](https://docs.railway.com/guides/fastapi)
- [Deploying a Monorepo — Railway Docs](https://docs.railway.com/deployments/monorepo)
