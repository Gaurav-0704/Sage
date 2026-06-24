# Deploying Sage to Railway

Two ways to deploy. **Single-service is the easy one — use it for review/testing.**

| | Single service (recommended) | Two services |
|---|---|---|
| What | FastAPI serves the React app **and** the API | Separate backend + frontend |
| Services | 1 + Postgres | 2 + Postgres |
| CORS | none (same origin) | must configure |
| Root Directory | **repo root (default)** | `backend` and `frontend` |

The API is always served under **`/api`**; the React app is served at `/`.

---

## A) Single-service deploy (recommended)

1. Push this repo to GitHub.
2. Railway → **New Project → Deploy from GitHub repo** → pick this repo.
   Leave **Root Directory empty** (repo root). Railway finds the root `Dockerfile`,
   builds the React app, and serves everything from one container.
3. **+ New → Database → Add PostgreSQL.**
4. On the app service → **Variables**:
   - `DATABASE_URL` → **Add Reference → Postgres → DATABASE_URL**
     (`postgres://` is auto-normalized to `postgresql://`).
   - `SECRET_KEY` → a long random string.
   - *(optional)* `ANTHROPIC_API_KEY`, email (`RESEND_API_KEY` or `SMTP_*`),
     payments (`RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET`).
   - *(optional)* `SEED_DEMO=true` → fills sample students/teachers/marks for a
     demo. **Leave it unset for a clean app** (the default).
5. **Settings → Networking → Generate Domain.** Open it — you're done.

`alembic upgrade head` runs on every deploy (no data dropped). The frontend's
API base is baked to `/api` at build time, so there's nothing else to configure.

## First sign-in

The backend seeds two logins on first boot (`seed_defaults` in `main.py`):

- **Owner** — `owner@sage.school` / `owner123`
- **Staff** — `staff@sage.school` / `staff123`

**Change these passwords immediately** (Settings → Sign in & security). A fresh
deploy is otherwise empty — add real students/teachers from the owner UI, and set
your school details in **Settings → School details**.

---

## B) Two-service deploy (separate backend + frontend)

Use this if you want independent scaling. Each service sets its **Root Directory**
and builds from that folder's `Dockerfile`.

> ⚠️ If you forget the Root Directory you get
> `Railpack could not determine how to build the app` — that means Railway is
> building from the repo root. Set the Root Directory (below) to fix it.

1. **Backend service** → Settings → **Root Directory: `backend`**.
   - Build/start come from `backend/Dockerfile` (`alembic upgrade head` then
     `uvicorn … --port $PORT`).
   - Variables: `DATABASE_URL` (Postgres reference), `SECRET_KEY`,
     `ALLOWED_ORIGINS` = the frontend URL (set after the next step), plus any
     optional keys.
   - Generate a domain.
2. **Frontend service** (same repo) → Settings → **Root Directory: `frontend`**.
   - Builds `frontend/Dockerfile` → `serve -s build -l $PORT`.
   - Variable: `REACT_APP_API_BASE` = `<backend-url>/api`. CRA bakes this at
     **build time**, so redeploy after changing it.
   - Generate a domain, then set the backend's `ALLOWED_ORIGINS` to it and redeploy
     the backend.

---

## Database migrations (Alembic)

- Schema is versioned in `backend/migrations/`; `migrations/env.py` reads the same
  env-driven `DATABASE_URL` as the app (SQLite locally, Postgres on Railway).
- `alembic upgrade head` runs on every deploy. After changing models:
  ```bash
  cd backend
  alembic revision --autogenerate -m "describe change"
  alembic upgrade head
  ```

## Local development

```bash
# Backend (SQLite, no env needed)  → http://127.0.0.1:8000  (API under /api)
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# Frontend  → http://localhost:3000  (talks to 127.0.0.1:8000/api)
cd frontend && npm install && npm start
```

Run the single-service build locally:
```bash
cd frontend && REACT_APP_API_BASE=/api npm run build && cd ..
FRONTEND_BUILD_DIR=$PWD/frontend/build uvicorn main:app --app-dir backend
# open http://127.0.0.1:8000  (set SEED_DEMO=true first for sample data)
```

## Troubleshooting

- **`Railpack could not determine how to build the app`** → only happens in the
  two-service flow when a service's Root Directory is still the repo root. Set it
  to `backend` / `frontend`. (Single-service uses the root `Dockerfile` and needs
  no Root Directory change.)
- **Frontend loads but API calls fail** (two-service only) → `REACT_APP_API_BASE`
  must end in `/api`, and the backend `ALLOWED_ORIGINS` must list the frontend URL.
- **502 right after deploy** → check the deploy logs for `alembic upgrade head`; a
  bad `DATABASE_URL` reference is the usual cause.

## Notes

- **Uploads** (assignment files) write to the container's **ephemeral** disk and
  don't survive redeploys — attach a Railway **Volume** at `backend/uploads/` (or
  use object storage) for durability. The database is safe on Postgres.
- **Web push** is staged (service-worker listeners exist); email notifications work
  today, VAPID keys aren't wired yet.
