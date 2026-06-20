# Nagarjuna High School ERP

A complete school management system for K–10. Single codebase, four sign-in
roles, runs locally with one command, mobile-friendly UI, and uses CSV
files as the editable source of truth so the data stays portable.

Built with FastAPI on the backend and React on the frontend, organised as
a small ecosystem of independent agents — one for each job (students,
fees, finance, exams, and so on). The agents share a database but never
import each other, so each one can be edited or replaced without
disturbing the rest.

> Originally built as an end-to-end full-stack project. See
> [DOCUMENTATION.md](./DOCUMENTATION.md) for the full guidebook covering
> architecture, calculations, and the design decisions behind each piece.

---

## What it can do

**For the school owner**
- A live dashboard with student totals, fees collected, expenses, cash
  and bank balances — all computed from the underlying transactions, no
  stored balances to drift out of sync.
- Manage students, teachers, fee structures, payments, and expenses.
- Print Bonafide certificates, Transfer Certificates and exam memos
  from a dedicated Records page (formal A4 layouts, browser-print).
- Approve new staff and teacher signups.
- Read every system action in the audit log.
- Run a self-check scanner that reports any database, import, or lint
  problems — runs every night and on demand.
- Talk to an in-built assistant in plain English that proposes changes
  and only applies the ones the owner approves.

**For the front office (cashier role)**
- A POS-style tile dashboard with one tap per fee head.
- Tap a tile, pick the student and amount, and the printable receipt
  pops up automatically.
- A simple class-wise student roster (names + class only — no Aadhaar,
  no admission number, no money information).

**For teachers**
- Their own dashboard, their classes, their assignments.
- Owner can grant front-office access so a teacher can also collect fees.

**For students**
- A personal dashboard showing the latest exam score, upcoming
  assignments, and the next exam date.
- Subject-wise marks, class-rank comparisons, and a small mind games
  page (memory match, math blitz, reaction time) for the fun bit.

**Across the board**
- Sign-up flow with role picker and owner approval queue.
- Forgot password with email-delivered six-digit code.
- Two-way CSV sync — open `data/seed_students.csv` in Excel, edit it,
  upload it, the database merges. Edit a student in the UI and the CSV
  rewrites itself. Same for teachers.
- Printable receipt for every payment and expense.
- Mobile layout with a hamburger menu, tested on iOS Safari and
  Android Chrome.
- Warm semi-dark UI with a polished theme.

---

## Quick start

You'll need Python 3.13 and Node.js 18 or newer.

```
git clone <this-repo>
cd "NHS App"
py run.py
```

That's it. The launcher creates a Python virtual environment, installs
backend dependencies, runs `npm install` for the frontend if needed,
then starts both servers and streams their output:

```
api  → http://127.0.0.1:8000   (Swagger docs at /docs)
web  → http://localhost:3000
```

On Windows you can also double-click `start.bat` instead.

To populate the database with 300 sample students, twelve sample
teachers, fee structures, exams, marks, and student logins:

```
py tools/seed_demo.py
```

Demo accounts:

| Role     | Email                                | Password    |
|----------|--------------------------------------|-------------|
| Owner    | owner@nagarjuna.school               | owner123    |
| Staff    | staff@nagarjuna.school               | staff123    |
| Teacher  | sunita.iyer@nagarjuna.school         | teacher123  |
| Student  | nhs0001@nagarjuna.school             | student123  |

---

## Architecture at a glance

```
                ┌────────────────────────────────────────┐
                │  React frontend (one app, four sidebars) │
                │  Sign-in → role-aware dashboard          │
                └─────────────────┬──────────────────────┘
                                  │ JSON over HTTP
                                  │ JWT in Authorization header
                ┌─────────────────┴──────────────────────┐
                │  FastAPI gateway                       │
                │  - audit middleware records every write│
                │  - CORS for the dev server             │
                │  - mounts every agent router           │
                └─────────────────┬──────────────────────┘
                                  │
        ┌──────┬──────┬───────────┼───────────┬───────┬───────┐
        ▼      ▼      ▼           ▼           ▼       ▼       ▼
      auth  students fees        finance   expenses  reports tiles
                          ────────┼────────
                          ▼               ▼
                       exams           teachers ─── assignments
                                          │
                                          ▼
                          teacher_self     student_self
                          ────────┼────────
                                  ▼
                          audit, scanner, ai, records

                     SQLite (single school.db file)
```

Sixteen agents, one job each. The pipeline is the same every time:

1. The user signs in. The auth agent issues a JWT carrying the user id
   and role.
2. The frontend stores the token and includes it on every request.
3. A FastAPI dependency reads the token, looks up the user, and rejects
   any request that doesn't have the right role for the endpoint.
4. The endpoint reads or writes the database via SQLAlchemy.
5. A middleware records the request in the audit log.
6. If the change touched a student or teacher record, a separate sync
   helper rewrites the corresponding CSV file on disk.

For everything else, see [DOCUMENTATION.md](./DOCUMENTATION.md).

---

## Tech stack

| Layer       | Tool                               | Why                                       |
|-------------|------------------------------------|-------------------------------------------|
| Backend     | Python 3.13, FastAPI, SQLAlchemy   | Fast to build, typed, async-ready         |
| Database    | SQLite (single file)               | Zero setup, easy backup, fits a single school |
| Auth        | JWT (python-jose) + bcrypt         | Standard, widely audited                  |
| Frontend    | React 19 + React Router            | Mature, familiar to most developers       |
| Charts      | Recharts                           | Lightweight, declarative                  |
| Styling     | Hand-written CSS variables         | No framework lock-in, easy to theme       |
| Launcher    | Custom Python script               | One command spins up both servers         |
| Optional AI | Anthropic Claude (via REST)        | Plain HTTP, no SDK dependency             |

No build step needed for the backend. The frontend uses Create React App
for hot reload during development.

---

## Project structure

```
NHS App/
├── README.md             ← you are here
├── DOCUMENTATION.md      ← full guidebook
├── LICENSE               ← CC BY-NC-SA 4.0
├── run.py                ← single-command launcher
├── start.bat             ← Windows double-click launcher
├── backend/              ← FastAPI service
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── dependencies.py
│   ├── audit_middleware.py
│   ├── csv_sync.py
│   ├── notifications.py
│   ├── school_constants.py
│   ├── requirements.txt
│   └── agents/
│       ├── auth_agent.py        ← sign in, sign up, password reset
│       ├── students_agent.py    ← students CRUD + CSV
│       ├── teachers_agent.py    ← teachers CRUD + CSV
│       ├── fees_agent.py        ← fee structures, bills, payments, receipt
│       ├── expenses_agent.py    ← expenses + voucher receipt
│       ├── finance_agent.py     ← live cash + bank
│       ├── reports_agent.py     ← dashboard, daily / monthly / yearly
│       ├── tiles_agent.py       ← configurable POS tiles
│       ├── exams_agent.py       ← exams + marks + per-student perf
│       ├── assignments_agent.py ← assignments per class/subject
│       ├── teacher_self_agent.py ← /teacher/me views
│       ├── student_self_agent.py ← /student/me views
│       ├── audit_agent.py       ← read-side of audit log
│       ├── scanner_agent.py     ← nightly self-check
│       ├── ai_agent.py          ← optional Claude assistant
│       └── records_agent.py     ← Bonafide / TC / Memo printing + master CSV
├── frontend/             ← React app
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── App.js
│       ├── api.js
│       ├── auth.js
│       ├── receipt.js
│       ├── preferences.js
│       ├── school.js
│       ├── components/
│       └── pages/
├── data/                 ← editable CSV source files
│   ├── seed_students.csv
│   ├── teachers.csv
│   └── students_master.csv  ← registrar's archive (auto-maintained)
└── tools/
    ├── seed_demo.py      ← creates 300 students + everything
    └── scan.py           ← static-analysis scanner for development
```

---

## License

Copyright © 2026 **Gaurav Singh Thakur**. All rights reserved.

This project is licensed under
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International](./LICENSE)
(CC BY-NC-SA 4.0).

In short:

- **Free to use, copy, modify, and share** — for non-commercial purposes.
- **Attribution required** — credit Gaurav Singh Thakur and keep the
  project name visible somewhere in the application.
- **Share-alike** — if you build on it, your version uses the same
  license.

For commercial deployment, please open an issue first.

---

## Contributing

Pull requests are welcome. The code is organised so each agent lives in
its own file — pick one and improve it without touching anything else.
Areas where help is especially welcome:

- Accessibility (screen readers, keyboard navigation).
- Regional language support (Hindi, Telugu, Kannada UI strings).
- Additional report formats (PDF rendering, Excel exports beyond CSV).
- More mind games for students.
- Real SMTP setup guides for forgot-password emails.

If you're new to the codebase, start with `DOCUMENTATION.md` — it walks
through every module.

---

## Acknowledgements

Thanks to the school staff and teachers whose feedback on real-world
workflows shaped the tile system, the receipt layout, and the role
boundaries between owner / staff / teacher / student.

Built and maintained by **Gaurav Singh Thakur**. If this project helps
your school or your learning, a star on the repository goes a long way.
