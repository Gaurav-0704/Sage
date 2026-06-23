# Sage — Verification Report (STEP 1 full scrape)

> Read-only inventory produced before any changes, per `CLAUDE_CODE_PROMPT.md`.
> Date: 2026-06-23. Scope: every backend source file and every `frontend/src` file.

---

## 1. Stack (confirmed from source)

- **Backend:** FastAPI 0.136.1 + SQLAlchemy 2.0.49, **SQLite** (`database.py` → `sqlite:///./school_v4.db`, hardcoded), JWT auth (python-jose + bcrypt). Agent-per-domain: 17 routers mounted in `main.py`.
- **Frontend:** Create React App (react-scripts 5.0.1) + React 19.2 + react-router-dom 6.27 + axios + recharts. No PWA service worker, no state lib.
- **AI:** Owner-only assistant (`ai_agent.py`) using `ANTHROPIC_API_KEY`; nightly `scanner_agent` + nightly `insights_agent`.
- **Notifications:** `notifications.py` already supports SMTP send (falls back to console) and persists to DB — but it is **not imported/called by any agent yet** (see gaps).

---

## 2. ORM models (`models.py`)

| Model | Table | Key columns |
|---|---|---|
| User | users | id, name, email(uniq), password, role(owner\|staff\|teacher\|student), status, can_do_front_office, created_at |
| PasswordResetCode | password_reset_codes | user_id, code, expires_at, used |
| Notification | notifications | to_email, subject, body, kind, delivered, created_at |
| Student | students | user_id, admission_no(uniq), name, aadhaar, dob, gender, student_class, section, parent_name, phone, address, photo_url, last_year_dues, status, admission_date |
| Teacher | teachers | user_id(uniq), employee_id(uniq), subject, classes_taught(csv str), qualification, phone, joined_date, photo_url |
| Assignment | assignments | teacher_id, student_class, section, subject, title, description, due_date, max_marks |
| FeeStructure | fee_structures | student_class, academic_year, tuition/transport/books/uniform/other_fee |
| Fee | fees | student_id, academic_year, total_fee, paid_amount, due_amount, due_date |
| Payment | payments | student_id, amount, date, mode, fee_head, reference, note, received_by |
| Expense | expenses | title, amount, category, paid_from, date, note, created_by |
| Account | accounts | name(uniq: cash\|bank), opening_balance |
| Exam | exams | name, academic_year, student_class, date |
| Mark | marks | student_id, exam_id, subject, max_marks, marks_obtained |
| AuditLog | audit_logs | user_id, user_name, user_role, method, path, status_code, summary, details, ip, created_at |
| ScannerRun | scanner_runs | started/finished_at, triggered_by, status, issues_count, summary, findings |
| AIConversation / AIMessage | ai_conversations / ai_messages | chat history + proposed actions |
| Tile | tiles | label, kind(payment\|expense), category, fee_head, icon, color, sort_order, active |
| AIInsight | ai_insights | category, severity, title, body, action_hint, generated_at, dismissed |
| TeacherClass | teacher_classes | teacher_id, student_class (normalised join) |

`main.py::_migrate()` does ad-hoc `ALTER TABLE ADD COLUMN` migrations (no Alembic).

---

## 3. API routes (method + path + role guard)

**auth** (`/auth`): POST `/login` (public), POST `/signup` (public), GET `/pending` (owner), POST `/users/{id}/approve` (owner), POST `/users/{id}/reject` (owner), POST `/forgot` (public), POST `/reset` (public), GET `/me` (any), PUT `/me` (any), PUT `/me/password` (any), POST `/users` (owner), GET `/users` (owner), DELETE `/users/{id}` (owner), GET `/notifications` (owner).

**students** (`/students`): GET `/roster` (school_member), GET `/by-class` (school_member), GET `/{id}/profile` (school_member), GET `` (owner), GET `/{id}` (owner), POST `` (owner), PUT `/{id}` (owner), DELETE `/{id}` (owner), GET `/export.csv` (owner), GET `/template.csv` (owner), POST `/import` (owner, **CSV only**).

**teachers** (`/teachers`): GET `` (owner), POST `` (owner), PUT `/{id}` (owner), DELETE `/{id}` (owner), GET `/export.csv` (owner), GET `/template.csv` (owner), POST `/import` (owner, **CSV only**).

**fees**: GET/POST `/fee-structures` (owner), POST `/fee-structures/{id}/apply` (owner), GET `/fees` (owner), POST `/fees` (owner), GET `/payments` (owner), POST `/payments` (can_collect), GET `/payments/{id}/receipt` (can_collect, HTML).

**finance** (`/finance`): GET `/summary` (owner), PUT `/accounts/{name}` (owner).

**expenses** (`/expenses`): GET `` (owner), POST `` (can_collect), DELETE `/{id}` (owner), GET `/{id}/receipt` (can_collect, HTML).

**exams**: GET `/exams` (staff_or_owner), POST `/exams` (owner), DELETE `/exams/{id}` (owner), GET `/exams/{id}/marks` (staff_or_owner), POST `/exams/{id}/marks/bulk` (owner), GET `/students/{id}/exam-reports` (staff_or_owner), GET `/students/{id}/performance` (staff_or_owner).

**reports** (`/reports`): GET `/dashboard`, `/daily`, `/monthly`, `/at-risk`, `/yearly` (all owner).

**tiles** (`/tiles`): GET `` (can_collect), GET `/all` (owner), POST `` (owner), PUT `/{id}` (owner), DELETE `/{id}` (owner).

**assignments** (`/assignments`): GET `` (any user), POST `` (teacher), PUT `/{id}` (teacher), DELETE `/{id}` (teacher).

**teacher_self** (`/teacher`): GET `/me/dashboard`, `/me/classes`, `/me/students/{class}` (teacher).

**student_self** (`/student`): GET `/me/dashboard`, `/me/profile`, `/me/assignments`, `/me/marks`, `/me/performance`, `/me/upcoming-exams` (student).

**audit** (`/audit`): GET `/logs`, `/actors`, `/summary` (owner).

**scanner** (`/scanner`): POST `/run` (owner), GET `/runs`, `/runs/{id}` (owner).

**ai** (`/ai`): GET `/conversations`, `/conversations/{id}/messages` (owner), POST `/chat`, `/execute`, `/stream` (owner), DELETE `/conversations/{id}` (owner), GET `/status`, `/tools` (owner).

**insights** (`/insights`): GET `` (owner), POST `/generate` (owner), PATCH `/{id}/dismiss` (owner), GET `/snapshot` (owner).

**records** (`/records`): GET `/students` (owner), GET `/students/{id}/exams` (owner), GET `/master.csv` (owner), POST `/sync` (owner), GET `/bonafide/{id}` (owner, HTML), GET `/tc/{id}` (owner, HTML), GET `/memo/{id}/{exam_id}` (owner, HTML).

Audit middleware logs all POST/PUT/DELETE/PATCH globally.

---

## 4. Frontend routes & pages (`App.js`)

Public: `/login`, `/signup`, `/forgot`.

Inside `ProtectedRoute` + `Layout`:
- `/` → role dispatch (Dashboard / StaffDashboard / TeacherDashboard / StudentDashboard); `/settings` (all).
- Owner+Staff shared: `/students`, `/students/:id` (component swaps by role).
- **Owner-only** (`RoleRoute role="owner"`): `/teachers`, `/approvals`, `/fees`, `/finance`, `/expenses`, `/reports`, `/tiles`, `/marks`, `/notifications`, `/audit`, `/scanner`, `/assistant`, `/records`.
- **Teacher-only**: `/my-classes`, `/assignments`, `/quick-entry`.
- **Student-only**: `/my-marks`, `/my-assignments`, `/games`.

Roles in UI: **owner, staff, teacher, student** (no parent). Nav is defined per-role in `Layout.jsx`.

---

## 5. CSS / responsive approach

- Two files: `index.css` (647 lines, global design system + components) and `App.css` (38 lines).
- **Only ONE real breakpoint** across the whole app: `@media (max-width: 800px)` in `index.css` (plus 1 trivial one in App.css). The UI is **desktop-first** with a fixed sidebar `Layout`, not mobile-first.
- Heavy use of fixed sidebar + grid layouts; tables are not wrapped for horizontal scroll on phones; touch target sizing is not enforced.
- **Verdict:** far from mobile-first. STEP 4 requires a real mobile-first refactor (breakpoints, flexible grids, touch targets, scrollable tables, collapsible nav/drawer).
- PWA: `manifest.json` exists (CRA default, standalone display) but there is **no service worker** → not installable/offline, no web push. `package.json` has no PWA/workbox deps.

---

## 6. Deploy-readiness blockers (for STEP 5)

- `frontend/src/api.js` hardcodes `API_BASE = "http://127.0.0.1:8000"` → must become `REACT_APP_API_BASE`.
- `main.py` CORS `allow_origins` hardcoded to localhost:3000 → must read `ALLOWED_ORIGINS`.
- `database.py` hardcodes SQLite URL → must read `DATABASE_URL` (Postgres) with SQLite fallback; no Alembic.
- `.env.example` exists but documents only `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `SECRET_KEY`. Missing `DATABASE_URL`, SMTP/Resend, Razorpay, `REACT_APP_API_BASE`, `ALLOWED_ORIGINS`.
- `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml` exist; no `railway.json`/`Procfile`.

---

## 7. Confirmed gap list vs. target features

| Target (from work order) | Status today | Gap |
|---|---|---|
| **STEP 2 — Excel sync + manual entry** | CSV import/export/template exist for students & teachers (`students_agent`, `teachers_agent`, `csv_sync.py`); manual "Add" forms exist. **No `.xlsx` support, no openpyxl/pandas.** | Add `.xlsx`/`.csv` import + xlsx export + xlsx template; structured `{created,updated,skipped,errors}` summary; ensure manual entry & import share one upsert path; audit log entries. |
| **TIER 1a — Attendance** | ❌ none | New `Attendance` model + agent + teacher-mark / owner-parent-student views. |
| **TIER 1b — Timetable** | ❌ none | New timetable models + conflict detection + teacher/student views. |
| **TIER 1c — Parent role + portal** | ❌ only owner/staff/teacher/student | Add `parent` role, parent↔student link, portal pages, RBAC. |
| **TIER 1d — Real notifications** | ⚠️ `notifications.py` can send SMTP but is **never called**; `Notification` rows only written by that unused helper | Wire sender into events (admission, payment, marks, notices); add web push; env keys. |
| **TIER 2 — Report-card PDF** | ⚠️ HTML bonafide/TC/memo exist in `records_agent`; no graded report card / PDF | Add report-card generation. |
| **TIER 2 — Assignment submission+grading** | ⚠️ assignments CRUD only; no submission/upload/grading | Add submission model + flow → marks. |
| **TIER 2 — Online fee payment** | ⚠️ manual payments only | Add Razorpay (₹/en-IN, reuse `fmtINR`). |
| **TIER 2 — Announcements / notice board** | ❌ none | Add broadcast model + filterable views. |
| **STEP 4 — Mobile-first + PWA** | ⚠️ 1 breakpoint, no SW | Mobile-first refactor + service worker + push. |
| **STEP 5 — Railway/Postgres** | ⚠️ blockers above | Env-drive URLs/CORS/DB, Alembic, deploy configs, DEPLOY.md. |

**Bottom line:** the three defining SMS features — attendance, timetable, parent portal — are entirely missing, and notifications are built but unwired. STEP 2 (Excel) is a meaningful extension of the existing CSV path rather than greenfield. Everything else aligns with the gap analysis already in `SAGE_GAP_ANALYSIS_AND_DEPLOY_PLAN.md`.
