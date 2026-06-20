# Sage — A Complete Guidebook

> Copyright © 2026 Gaurav Singh Thakur. Licensed under CC BY-NC-SA 4.0.
> See [LICENSE](./LICENSE) for terms.

This document is the long-form companion to the README. The README will
get you running in five minutes; this one walks through every piece of
the system in enough detail that another developer could pick it up,
understand it, and confidently change it.

---

## Table of contents

1. [What this project is and why it exists](#1-what-this-project-is-and-why-it-exists)
2. [System architecture](#2-system-architecture)
3. [Tech stack and the reasoning behind each choice](#3-tech-stack-and-the-reasoning-behind-each-choice)
4. [Setup and first run](#4-setup-and-first-run)
5. [Roles and permission model](#5-roles-and-permission-model)
6. [The agent ecosystem](#6-the-agent-ecosystem)
7. [Data model](#7-data-model)
8. [Money flow and calculations](#8-money-flow-and-calculations)
9. [Authentication pipeline](#9-authentication-pipeline)
10. [The quick tile (front-office) system](#10-the-quick-tile-front-office-system)
11. [Receipts](#11-receipts)
12. [Two-way CSV sync](#12-two-way-csv-sync)
13. [The owner's assistant](#13-the-owners-assistant)
14. [Background scanner](#14-background-scanner)
15. [Audit log](#15-audit-log)
16. [Settings and preferences](#16-settings-and-preferences)
17. [Mobile and accessibility](#17-mobile-and-accessibility)
18. [Mind games](#18-mind-games)
19. [Known limitations](#19-known-limitations)
20. [Future work](#20-future-work)
21. [Glossary](#21-glossary)

---

## 1. What this project is and why it exists

Many small private schools in India still run their fee collection on
paper receipt books, their admission registers in spreadsheets, and
their exam marks in separate notebooks per teacher. Each system is
fine on its own; together they create reconciliation work that
swallows hours every month.

The Sage is an attempt to bring all of that
into one application that:

- A non-technical owner can run on a single laptop.
- A front-office clerk can use like a point-of-sale terminal.
- A teacher can use to manage assignments and grades.
- A student or parent can use to check progress.

It's intentionally small. There is no Kubernetes, no Redis, no message
queue, no microservice mesh. It is one Python service, one React app,
and one SQLite database file. That is enough for a school of a few
hundred students, which is the size most of these schools are.

The system is designed so each piece can be replaced. If a school
already uses Tally for accounting, the finance agent can be ignored.
If a school uses a different exam pattern, only the exams agent needs
adjusting. The agents share a database but never call each other
directly, which keeps the blast radius of any change small.

---

## 2. System architecture

The whole system is three parts: a frontend, a backend, and a database.
The backend is internally split into fifteen agents, each owning one
domain.

```
                    ┌──────────────────────────────┐
                    │   Browser (React app)        │
                    │   Single sign-in screen      │
                    │   Role-aware sidebar         │
                    └──────────────┬───────────────┘
                                   │ JSON over HTTP
                                   │ JWT in Authorization
                                   ▼
            ┌───────────────────────────────────────────┐
            │         FastAPI gateway (main.py)         │
            │  Audit middleware  •  CORS  •  Routers    │
            └───┬─────┬─────┬─────┬─────┬─────┬─────┬───┘
                │     │     │     │     │     │     │
                ▼     ▼     ▼     ▼     ▼     ▼     ▼
              auth  students fees finance expenses reports tiles
                                  ─────┬─────
                                       ▼
                              exams · teachers · assignments
                              teacher_self · student_self
                              audit · scanner · ai
                                       │
                                       ▼
                              SQLite (one file)
```

Each agent is a Python module under `backend/agents/`. They share three
things:

1. **Models** — declared once in `models.py`, all agents query the same
   tables.
2. **Schemas** — Pydantic models in `schemas.py`, used for request /
   response validation.
3. **Dependencies** — `dependencies.py` defines the small set of
   permission guards (`require_owner`, `require_can_collect`, etc.).

That's the only coupling. An agent never imports another agent's
router or function. If a change is needed in the way fees work, only
`fees_agent.py` is touched.

---

## 3. Tech stack and the reasoning behind each choice

| Layer       | Tool                                  | Why                                                                 |
|-------------|---------------------------------------|---------------------------------------------------------------------|
| Backend     | Python 3.13 + FastAPI                 | Type hints, fast iteration, automatic OpenAPI docs                  |
| ORM         | SQLAlchemy 2 (Core + ORM)             | The default in the Python ecosystem; widely understood              |
| Database    | SQLite (single `school_v4.db` file)   | No daemon to install; the entire database is one file you can copy  |
| Auth        | JWT via `python-jose`                 | Stateless, easy to verify, standard in single-page apps             |
| Hashing     | `bcrypt`                              | Slow by design; the right choice for password storage               |
| Frontend    | React 19 + React Router 6             | Mature, large hiring pool                                           |
| Charts      | Recharts                              | Declarative, integrates cleanly with React state                    |
| Styling     | Hand-written CSS with custom properties | No framework lock-in; theming via a single set of variables       |
| Launcher    | A small Python script (`run.py`)      | Wraps the messy "create venv, install, start two processes" dance   |
| Optional AI | Anthropic Claude via plain HTTP       | Stays a soft dependency — no Python SDK needed                      |

The deliberate choices here are: SQLite over Postgres (because the
school doesn't need replication), CRA over Next.js (because we don't
need server-side rendering), and a launcher script over Docker (because
the target user is a school owner, not a DevOps engineer).

---

## 4. Setup and first run

The launcher does everything in one shot.

```
py run.py
```

What happens, in order:

1. **Virtual environment** — if `backend/.venv` doesn't exist, the
   launcher creates one using `py -3.13 -m venv` (or falls back to the
   default Python on the path).
2. **Backend install** — if `fastapi`, `uvicorn`, `pydantic`,
   `multipart`, `jose`, or `bcrypt` can't be imported, `pip install -r
   requirements.txt` runs once.
3. **Frontend install** — if `frontend/node_modules/react-router-dom`
   or `recharts` is missing, `npm install` runs.
4. **Boot** — `uvicorn main:app --reload` on port 8000, `npm start` on
   port 3000. Both outputs are interleaved with `[api]` and `[web]`
   prefixes in the same terminal.
5. **Database** — `Base.metadata.create_all` creates any missing
   tables; a small migration block adds new columns to existing tables
   if you're upgrading.
6. **Seed defaults** — owner and staff demo accounts, the cash and
   bank account rows, and a starter set of quick tiles are inserted if
   they don't exist.
7. **Scheduler** — the nightly scanner background loop starts and
   sleeps until 02:00.

To populate three hundred students, twelve teachers, fee structures,
exams with marks, and student logins, run the seeder in a second
terminal:

```
py tools/seed_demo.py
```

The seeder is idempotent — running it twice does the right thing.

---

## 5. Roles and permission model

There are four roles, each with a distinct purpose and a distinct
sidebar.

| Role     | What they see                                                                                       |
|----------|-----------------------------------------------------------------------------------------------------|
| Owner    | Everything: dashboard, students, teachers, fees, expenses, finance, reports, tiles, marks, assistant, scanner, audit, notifications, settings. |
| Staff    | A class-wise student roster (names + class only) and the quick-entry tile dashboard.                |
| Teacher  | Their own dashboard, the classes they teach, and the assignments they've created. Plus the tile dashboard if the owner has flagged them with front-office access. |
| Student  | A personal dashboard, their own marks history, their assignments, mind games.                       |

The sensitive fields (Aadhaar, admission number, fee history) are only
exposed to the owner. The students agent enforces this at the API
layer — staff and teachers calling `/students/{id}` get a 403; they can
only call `/students/{id}/profile`, which returns a sanitised view.

Permission guards are a small, named set:

- `require_owner` — owner only.
- `require_staff_or_owner` — admin operations the owner has delegated.
- `require_teacher` — teacher-only operations like creating an
  assignment.
- `require_student` — student-only `/me` views.
- `require_can_collect` — owner, staff, or a teacher with the
  `can_do_front_office` flag. Used by payment and expense endpoints.
- `require_school_member` — anyone signed in. Used by routes that need
  authentication but not a specific role (the safe student roster).

Each guard is a one-screen function in `dependencies.py`. They compose
naturally with FastAPI's `Depends()`.

---

## 6. The agent ecosystem

The agents fall into four groups by their job.

**Identity and access**
- `auth_agent` — sign in, sign up, password reset, current-user
  endpoints, owner approval queue.

**Records management**
- `students_agent` — student CRUD, roster views, CSV import/export.
- `teachers_agent` — teacher CRUD, CSV import/export.
- `assignments_agent` — assignment CRUD scoped to the teacher who
  created it.

**Money**
- `fees_agent` — fee structures, applying structures to a class,
  recording payments, the printable fee receipt.
- `expenses_agent` — expense CRUD, the printable expense voucher.
- `finance_agent` — live cash and bank balance, opening balance.
- `tiles_agent` — the configurable tiles that drive the front-office
  dashboard.

**Academics and reporting**
- `exams_agent` — exams + marks + per-student performance.
- `reports_agent` — dashboard totals and the daily / monthly / yearly
  rollups.

**Self-views**
- `teacher_self_agent` — `/teacher/me` endpoints.
- `student_self_agent` — `/student/me` endpoints.

**Operations**
- `audit_agent` — read-only browser for the audit log.
- `scanner_agent` — nightly self-check + on-demand run.
- `ai_agent` — optional assistant that proposes changes for the owner
  to confirm.

The fact that these are separate files matters more than where any
single endpoint lives. If the owner wants to switch the receipt format
to GST-compliant invoices, the change is contained in
`fees_agent.py::_receipt_html()`. Nothing else needs to know.

---

## 7. Data model

Here are the tables, grouped by which agent owns them.

**users**
```
id, name, email (unique), password (bcrypt hash),
role (owner|staff|teacher|student), status (active|pending|disabled),
can_do_front_office, created_at
```

**students**
```
id, user_id (nullable, links to a student login),
admission_no (unique), name, aadhaar, dob, gender,
student_class (KG1..10), section, parent_name, phone, address,
photo_url, last_year_dues, status (active|inactive|alumni),
admission_date, created_at
```

**teachers**
```
id, user_id (links to login), employee_id (unique), subject,
classes_taught (CSV: "5,6,7"), qualification, phone, joined_date,
photo_url, created_at
```

**fee_structures**
```
id, student_class, academic_year ("2025-26"),
tuition_fee, transport_fee, books_fee, uniform_fee, other_fee
```

**fees** (one row per student per academic year)
```
id, student_id, academic_year, total_fee, paid_amount, due_amount,
due_date, created_at
```

**payments**
```
id, student_id, amount, date, mode (cash|bank), fee_head,
reference (cheque #/UTR), note, received_by (user_id), created_at
```

**expenses**
```
id, title, amount, category (salary|utilities|supplies|...),
paid_from (cash|bank), date, note, created_by (user_id), created_at
```

**accounts** (just two rows: cash and bank)
```
id, name, opening_balance, updated_at
```

**exams**
```
id, name ("Term 1"), academic_year, student_class, date, created_at
```

**marks**
```
id, student_id, exam_id, subject, max_marks, marks_obtained, created_at
```

**tiles**
```
id, label, kind (payment|expense), category, fee_head,
icon (emoji), color, sort_order, active, created_at
```

**assignments**
```
id, teacher_id, student_class, section, subject, title,
description, due_date, max_marks, created_at
```

**Operational tables** (filled in by the system, not the user)
```
audit_logs       id, user_id, user_name, user_role, method, path,
                 status_code, summary, details, ip, created_at

scanner_runs     id, started_at, finished_at, triggered_by, status,
                 issues_count, summary, findings (JSON)

notifications    id, to_email, subject, body, kind, delivered, created_at

password_reset_codes  id, user_id, code, expires_at, used

ai_conversations id, user_id, title, created_at
ai_messages      id, conversation_id, role, content, actions, executed,
                 created_at
```

The schema is small enough to fit in one file (`models.py`) and is
loaded by every agent that touches the database. New tables added in
later versions are picked up automatically by `Base.metadata.create_all()`;
new columns on existing tables are added by a tiny migration block in
`main.py::_migrate()` that runs on each startup.

---

## 8. Money flow and calculations

This is the most important section. Mistakes here corrupt the school's
financial picture, so the rules are kept small and checked in code.

**Per-student totals**
```
total_fee_for_student = sum(this-year fee bills) + last_year_dues
total_paid_for_student = sum(payments)
outstanding_for_student = max(0, total_fee_for_student - total_paid)
credit_for_student      = max(0, total_paid - total_fee_for_student)
```

The `max(0, ...)` clamps mean a student who overpaid never shows
"negative dues"; the credit shows up as a positive balance instead.

**Cash and bank balances** (the single most-asked question on the
dashboard)
```
balance("cash") = opening_balance("cash")
                + sum(payments where mode = "cash")
                - sum(expenses where paid_from = "cash")

balance("bank") = opening_balance("bank")
                + sum(payments where mode = "bank")
                - sum(expenses where paid_from = "bank")
```

These are computed on every request to `/finance/summary` —
nothing is stored. The advantage: the moment a payment is recorded
(through any path — UI, tile, CSV import, the assistant), the
balances reflect it on the next page load. There is no separate
"recompute" step that can be missed.

**Settlement order when a payment comes in**
```
remaining = payment.amount

# 1. Apply to outstanding fee bills (oldest first by id)
for each open fee row:
    applied = min(remaining, fee.due_amount)
    fee.paid_amount += applied
    fee.due_amount  -= applied
    remaining       -= applied

# 2. Then last-year carry-forward dues
if remaining > 0 and student.last_year_dues > 0:
    applied = min(remaining, student.last_year_dues)
    student.last_year_dues -= applied
    remaining              -= applied

# 3. Anything left becomes a credit on the student
#    (visible as paid > total_billed)
```

This was the most subtle bug to catch in earlier versions — the loop
was applying only to current-year `fees` rows and ignoring
`last_year_dues`, which meant a student with only carry-forward dues
saw their payment recorded but their dues stayed put.

**Dashboard rollup**
```
total_fee_value = sum(all fees.total_fee) + sum(all students.last_year_dues)
total_collected = sum(all payments.amount)
total_due       = max(0, total_fee_value - total_collected)
total_expense   = sum(all expenses.amount)
net             = total_collected - total_expense
```

Every report — daily, monthly, yearly — is built from the same three
tables (`payments`, `expenses`, `fees`). There is no separate
ledger. The trade-off: the queries get slightly more expensive over
time, but for a school of a few hundred students it is comfortably
under a second.

**Validation rules** (all enforced server-side, not in the UI):

- Payment amount must be > 0 and a finite number.
- Mode must be `cash` or `bank`.
- Expense category must be in the allowed set.
- Expense title cannot be blank.
- Opening balance can be set to any value (positive or negative —
  schools sometimes carry forward losses).

These are checked even if the request comes through the assistant or
the CSV import path.

---

## 9. Authentication pipeline

The login flow is intentionally simple.

```
┌───────────┐   email + password    ┌─────────────────┐
│ Browser   │ ──────────────────►   │ /auth/login     │
│ (React)   │                       │ (auth_agent)    │
└─────┬─────┘                       └────────┬────────┘
      │                                       │
      │                                       ▼
      │                       hash check (bcrypt.checkpw)
      │                                       │
      │                                       ▼
      │                              create JWT (HS256)
      │                                       │
      │ JWT + user object (JSON)             │
      │ ◄────────────────────────────────────┘
      ▼
  localStorage:
    sage_token, sage_user
      │
      │ on every request
      ▼
  axios interceptor adds:
    Authorization: Bearer <jwt>
      │
      ▼
  ┌───────────────────────────────────────┐
  │ FastAPI dependency get_current_user   │
  │  - decode JWT                         │
  │  - load User row                      │
  │  - reject if status != "active"       │
  └─────────────────┬─────────────────────┘
                    ▼
            role guard (require_owner, etc.)
                    ▼
              endpoint runs
```

A few details worth knowing:

- The JWT carries the user id and role and expires in 12 hours.
- Bcrypt is called directly (not via `passlib`) because passlib's
  internal self-check breaks on bcrypt 5+. The truncation to 72 bytes
  is done explicitly.
- Password change requires the old password — even for the owner.
- Forgot password generates a six-digit code, stores it with a
  fifteen-minute expiry, and sends it via email if SMTP is configured
  or logs it to the console + notifications table if not. The reset
  endpoint then verifies the code and updates the password.

The signup flow is slightly more involved because of the approval
queue. Students self-activate when their `admission_no` matches an
existing student record. Staff and teachers land in `pending` status
and the owner sees them on the **Approvals** page.

---

## 10. The quick tile (front-office) system

The `tiles` table holds a configurable grid of buttons that drive the
front-office cashier flow. Each tile has:

- a label and emoji icon
- a color (used for the gradient background)
- a kind: `payment` or `expense`
- the relevant fee head or expense category
- a sort order

The owner manages tiles on the **Quick Tiles** page — add, edit,
disable, delete. Reordering is by `sort_order`. The staff and any
teacher with front-office access see the same tiles on their
dashboard.

The flow when a tile is tapped:

```
tap tile → modal opens → if payment: pick student + amount + cash/bank
                          if expense: amount + cash/bank + optional note
                       → submit → POST /payments or /expenses
                       → backend validates, writes the row
                       → the printable receipt opens automatically
                       → modal closes
```

The reason the tiles are stored in the database (rather than
hard-coded) is that different schools have different fee heads. A
boarding school might have a "Mess fee" tile; a tuition centre might
have "Hall Fee". The owner adjusts without a developer needing to
change code.

---

## 11. Receipts

Every payment and every expense produces a printable receipt. They are
HTML pages that auto-trigger the browser's print dialog when they
load — meaning the user can pick a real printer or "Save as PDF" from
the destination dropdown without learning a new format.

**Fee receipt** (`GET /payments/{id}/receipt`)
- School name header
- Receipt number (zero-padded)
- Student name, admission number, class, parent
- Date, mode (CASH/BANK), fee head, optional reference
- Amount in a highlighted box
- A footer noting it's system-generated

**Expense voucher** (`GET /expenses/{id}/receipt`)
- Same school header
- Voucher number (`EXP000123`)
- Description, category, date, paid-from
- Optional note
- Amount in an orange-accented box (visually reads as an outflow)

Both endpoints require `require_can_collect` — owner, staff, or a
teacher with front-office access. They return raw HTML so the
frontend can simply pop it in a new window using `window.open()`.

The receipt size is A5, printable on most desk-side printers and
clean on phone "save to PDF" exports.

---

## 12. Two-way CSV sync

Schools that have a long history of running on spreadsheets are more
comfortable when they can see their data in Excel. The CSV sync makes
the file system a first-class peer to the database.

**The two CSVs live in `data/`:**
- `data/seed_students.csv` — the editable source for students.
- `data/teachers.csv` — same for teachers.

**Direction one: database to file** (automatic)

Every time a student or teacher row is created, updated, or deleted —
through the UI, a CSV upload, or the assistant — a small helper in
`csv_sync.py` runs after the commit. It queries the full table and
rewrites the CSV from scratch. The file always reflects "what the
database says now".

**Direction two: file to database** (manual)

The owner can edit the CSV in Excel, then click "Upload CSV" on the
Students or Teachers page. The import endpoint:

1. Parses each row, validating required fields and date formats.
2. Looks for an existing row with the same key (`admission_no` for
   students, `employee_id` for teachers).
3. Updates if found, creates if not.
4. Returns a summary: how many created, updated, and skipped, plus
   row-by-row errors.
5. Re-exports the CSV so the on-disk file matches the merged state
   (handles the case where the user uploaded a partial file).

**Why both directions?** Because the file and the database can drift
otherwise. With auto-export, the file is always a faithful mirror.
With upload-on-demand, the user can use the file as a bulk-edit tool
without losing work to a database reset.

---

## 13. The owner's assistant

The optional Anthropic-powered assistant lives in `agents/ai_agent.py`.
It gives the owner a way to make changes by typing in plain English,
with the strict constraint that the assistant only ever proposes
actions — the owner clicks Apply.

The pipeline:

```
owner types a message
        │
        ▼
POST /ai/chat
        │
        ▼
backend builds the conversation history
(includes earlier user / assistant turns)
        │
        ▼
POST to api.anthropic.com/v1/messages
with: system prompt + tools + messages
        │
        ▼
Claude returns content blocks:
  - text (an answer or a clarifying question)
  - tool_use (a proposed action with arguments)
        │
        ▼
backend persists the assistant message
(actions stored as JSON, executed=false)
        │
        ▼
frontend renders proposed actions as a list of
  - checkbox (include / exclude)
  - editable JSON of the parameters
  - red badge if destructive
        │
        ▼
owner clicks "Apply N action(s)"
        │
        ▼
POST /ai/execute
  body: { conversation_id, message_id,
          approved_action_ids, overrides }
        │
        ▼
backend runs each approved tool function
(e.g. _t_create_student) against the database
        │
        ▼
results returned + appended as a system message
in the conversation so the assistant sees the outcome
```

There are twenty-three tools at the time of writing, split into
read-only ones (`list_students`, `get_dashboard_stats`, etc.) and
write ones (`create_student`, `apply_fee_structure`, etc.). The
destructive ones (`delete_student`, `delete_teacher`) get an extra
confirmation in the browser.

The system prompt is strict: ask before guessing, verify with a list
tool before mutating, never invent a tool name. The whole point is
that the assistant is a planning aid, not an autopilot.

If `ANTHROPIC_API_KEY` is not set, the chat endpoint returns a clean
"not configured" error. The rest of the application is unaffected.

---

## 14. Background scanner

The scanner is a small cron-style task that runs nightly at 02:00 and
checks the system for problems. It does three things:

1. **Import check** — try to import every agent module. Catches the
   "I broke an import path" class of errors.
2. **Database check** — run a `SELECT … LIMIT 1` against every table.
   Catches schema drift or missing migrations.
3. **Lint** — if `ruff` is installed, run it across the backend and
   pick up the first fifty findings.

Each finding has a severity (`error` or `warning`), a category, a
location, and a detail message. They're saved to the `scanner_runs`
table and a notification with the summary is sent to every owner.

The owner can also trigger a scan on demand from the **Scanner**
page. The page lists every past run; clicking one shows the findings.

The schedule is implemented as an asyncio task started in the FastAPI
lifespan. It sleeps until the next 02:00 local time, runs a scan,
sleeps until the next 02:00, and so on.

---

## 15. Audit log

Every state-changing request is logged. The mechanism is a Starlette
middleware (`audit_middleware.py`) that:

1. Lets the request pass through normally.
2. After the response is produced, decodes the JWT (best-effort) to
   identify the user.
3. Maps the (method, path) to a friendly summary like "Recorded
   payment" or "Approved user".
4. Writes a row to the `audit_logs` table with the timestamp, user,
   role, method, path, status code, summary, and IP.

If the JWT is invalid or missing, the row is recorded as anonymous.
Failures inside the middleware are swallowed — audit must never break
the underlying write.

The owner browses the log on the **Audit Log** page with filters for
role, HTTP method, and time window. There's also a per-role activity
summary table showing how many POST / PUT / DELETE operations each
role has performed in the window.

---

## 16. Settings and preferences

The settings page is split into five sections so they're easy to find:

1. **Profile** — display name and email (the email is what the user
   signs in with).
2. **Sign in & security** — change password (requires the current
   password and a confirmation field).
3. **Display** — compact mode (tighter spacing) and font size (small
   / normal / large). These are saved per-device in `localStorage`
   and applied via `data-*` attributes on the `<html>` element so the
   CSS can react.
4. **Notifications** — email-on/off toggle (preference is stored
   locally for now; future versions will respect it server-side).
5. **Account** — read-only summary: role, status, email, and front-
   office access for teachers.

The local preferences module (`preferences.js`) is intentionally
small: a get / set / apply API over `localStorage` keyed by stable
constants. Every page that needs a preference imports from here.

---

## 17. Mobile and accessibility

The layout uses a single CSS file with one media-query breakpoint at
800px. Below that:

- The sidebar collapses behind a hamburger menu in the top bar.
- Tap targets are at least 44px tall (Apple's accessibility
  recommendation).
- Forms drop from a two-column grid to one column.
- The tile and class card grids drop to two columns from auto-fill.
- Tables get horizontal scroll instead of clipping.

The viewport meta tag is set with `viewport-fit=cover` so the layout
respects the iPhone notch. The theme color is set to the dark
background color so the iOS browser chrome blends in.

The whole app stays usable in both portrait and landscape on phones.
There is more accessibility work to do — proper ARIA labels and
keyboard navigation are on the future-work list.

---

## 18. Mind games

A small detour from the serious stuff: the student dashboard has a
**Mind Games** tab with three games meant to be a five-minute break
between assignments.

- **Memory Match** — sixteen cards face-down; flip pairs; matches
  stay revealed; track moves and elapsed time. A win banner appears
  with the score and a "play again" button.
- **Quick Math** — thirty-second blitz of addition, subtraction, and
  multiplication. Each correct answer increments the score and pulls
  up the next problem.
- **Reaction Time** — wait for green; tap as fast as you can; track
  the best time. Tapping early shows a friendly "too soon" message
  instead of recording a result.

All three are pure React components — no network calls, no shared
state. They're a good place to add more games (memory recall,
typing speed, basic logic puzzles).

---

## 19. Known limitations

Being honest about what this software does NOT do today:

- **Single-school deployment** — there is no `tenant_id` anywhere.
  Running multiple schools requires multiple instances.
- **No real-time updates** — the dashboard refreshes when reloaded,
  not via WebSockets. Two staff members entering payments at the
  same time will see each other's work after the next refresh.
- **Backups are manual** — copy `backend/school_v4.db` somewhere
  safe. There is no scheduled backup job.
- **No PDF library** — receipts are HTML; "Save as PDF" relies on
  the browser. For a server-generated PDF, a future version would
  add `weasyprint` or `reportlab`.
- **Sample marks are synthetic** — the seeder generates plausible
  scores with normal-ish distributions. They are not real student
  data.
- **No attendance module** — was on the v0.6 roadmap, hasn't been
  built yet.
- **Email requires SMTP** — without a configured SMTP server,
  "forgot password" codes only show in the console and the
  Notifications page; the user can't recover their own password
  without owner help.
- **Single-currency** — everything assumes Indian Rupees. The
  formatter is `₹X,XX,XXX` (Indian grouping).

These are honest gaps, not bugs. They're documented so a developer
considering this codebase for production knows what to plan for.

---

## 20. Future work

Roughly in priority order, the things this project would benefit from:

**High value, small effort**
- Attendance agent + tile + per-student record.
- Bulk payment import (CSV of student admission numbers + amounts).
- Photo upload for students and teachers.
- A backup-on-shutdown hook that copies the database file.

**High value, medium effort**
- Real PDF generation for receipts (server-side).
- WhatsApp / SMS reminders for overdue fees.
- Multi-language UI (Hindi, Telugu, Kannada).
- Accessibility pass (ARIA labels, keyboard nav, screen reader testing).
- Submission upload + grading workflow for assignments.

**Larger projects**
- Multi-school support with tenant_id throughout.
- Real-time updates via WebSockets.
- Mobile app wrapper (React Native or Capacitor) for offline use.
- Integration with payment gateways (Razorpay, PhonePe).
- Accounting export (Tally XML, GST-compliant invoices).

---

## 21. Glossary

- **Agent** — an isolated backend module owning one domain (students,
  fees, etc.). Implemented as a FastAPI router file. Despite the
  name, it has nothing to do with AI agents — the term is borrowed
  from the actor model in distributed systems.
- **Tile** — a configurable button on the front-office dashboard
  that maps to either a payment or an expense.
- **Front-office access** — a flag on a teacher's user row that
  lets them use the cashier tile dashboard.
- **Audit middleware** — the Starlette middleware that records every
  state-changing request to the audit log.
- **Sync helper** — `csv_sync.py`, the module that rewrites
  `data/*.csv` to mirror the database after every change.
- **Quick entry** — the staff and front-office name for the tile
  dashboard.
- **Roster** — the staff-safe view of students (name + class +
  section, no PII or money information).
- **Dashboard stats** — the rollup numbers at the top of the owner
  dashboard, all computed live from the underlying tables.
- **Reset code** — the six-digit code emailed for password reset.
  Stored in `password_reset_codes` with a fifteen-minute expiry.

---

## Appendix A: typical request, end to end

To make the architecture concrete, here's what happens when the staff
member taps the "Tuition Fee" tile, picks a student, enters ₹5,000,
and submits.

```
1. Staff is signed in. Their JWT is in localStorage.

2. The tile modal POSTs to /payments with:
       { student_id: 42, amount: 5000, mode: "cash",
         fee_head: "Tuition", date: "2026-04-26" }
   The Authorization header carries the JWT.

3. The audit middleware (still on the way in) does nothing — it only
   records on the way out.

4. FastAPI matches the route to fees_agent.make_payment.

5. The require_can_collect dependency runs:
       - decodes the JWT
       - loads the User row
       - confirms role is "staff" (or owner, or teacher with the
         front-office flag).

6. make_payment validates: amount > 0, mode in {cash, bank},
   student exists.

7. A Payment row is inserted with received_by = staff.id.

8. The settlement loop runs:
       - the student's open Fee rows (oldest id first) absorb the
         ₹5,000 against their due_amount.
       - if any remains, last_year_dues absorbs the rest.
       - any leftover sits as a credit (paid > total_billed).

9. db.commit() persists the Payment + the modified Fee/Student rows
   in one transaction.

10. The endpoint returns the new Payment row as JSON.

11. The audit middleware (now on the way out) runs:
        - decodes the JWT to identify the user
        - maps (POST, /payments) to summary "Recorded payment"
        - inserts an AuditLog row.

12. The frontend receives the response, calls openReceipt("payment", id),
    which fetches /payments/{id}/receipt (an HTML page) and writes it
    into a new window. That window auto-calls window.print().

13. Next time the owner loads the dashboard, /reports/dashboard
    recomputes:
        total_collected += 5000
        cash_balance     += 5000
        total_due        -= 5000
    All from live SQL, no separate update needed.
```

That's the whole vertical slice. Every other write in the system
follows the same shape.

---

## Appendix B: file map

```
Sage/
├── README.md                  — public-facing overview
├── DOCUMENTATION.md           — this guidebook
├── LICENSE                    — CC BY-NC-SA 4.0
├── run.py                     — single-command launcher
├── start.bat                  — Windows double-click
├── data/
│   ├── seed_students.csv      — editable student source (auto-synced)
│   └── teachers.csv           — editable teacher source (auto-synced)
├── backend/
│   ├── main.py                — gateway, mounts agents, lifespan
│   ├── database.py            — SQLAlchemy engine + session
│   ├── models.py              — every ORM model
│   ├── schemas.py             — every Pydantic schema
│   ├── auth.py                — bcrypt + JWT helpers
│   ├── dependencies.py        — get_db, role guards
│   ├── audit_middleware.py    — records every state-changing request
│   ├── csv_sync.py            — rewrites data/*.csv after each change
│   ├── notifications.py       — email helper (logs locally if no SMTP)
│   ├── school_constants.py    — shared constants (class order, paths)
│   ├── requirements.txt
│   └── agents/                — one file per domain (15 files)
└── frontend/
    ├── package.json
    ├── public/
    │   └── index.html
    └── src/
        ├── App.js             — routes
        ├── api.js             — axios + JWT interceptor
        ├── auth.js            — AuthProvider context
        ├── receipt.js         — opens the printable receipt window
        ├── preferences.js     — localStorage display preferences
        ├── school.js          — shared frontend constants
        ├── components/        — Layout, ProtectedRoute, RoleRoute,
        │                       CredentialsCard
        └── pages/             — one file per screen
```

---

That's the system. If anything in this document is unclear or out of
date, the source of truth is always the code — every file is small
enough to read in a single sitting.
