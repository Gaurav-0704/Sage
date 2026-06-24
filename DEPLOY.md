# Deploying Sage to Railway

Sage deploys as **two services in one repo** (backend + frontend) plus a
**Postgres** plugin.

```
Railway project
├── Postgres        (plugin → provides DATABASE_URL)
├── backend         (Root Directory: backend)   FastAPI + uvicorn
└── frontend        (Root Directory: frontend)   CRA build served by `serve`
```

Each service builds from its **own `Dockerfile`** (Railway always uses a
Dockerfile when it finds one). Both Dockerfiles bind `$PORT`, so they work on
Railway and under `docker-compose` unchanged.

> ⚠️ **The #1 deploy mistake — read this first.**
> A Railway service must have its **Root Directory** set to `backend` or
> `frontend`. If you deploy the repo without setting it, Railway tries to build
> from the repo root, finds no single app, and fails with:
>
> ```
> Railpack could not determine how to build the app.
> ```
>
> This is **not** a code problem — it means the service Root Directory is still
> the repo root. Fix it in **service → Settings → Root Directory** (steps below).

---

## 1. Create the project + Postgres

1. Push this repo to GitHub.
2. Railway: **New Project → Deploy from GitHub repo** → pick this repo.
3. **+ New → Database → Add PostgreSQL.** It exposes `DATABASE_URL`.

## 2. Backend service

1. On the service created in step 2 (or **+ New → GitHub Repo** → same repo) open
   **Settings**:
   - **Root Directory: `backend`**  ← required.
   - With the root set, Railway finds `backend/Dockerfile` and
     `backend/railway.json` and builds with the Dockerfile. Start command (from
     both the Dockerfile and `railway.json`):
     `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`
     — migrations run on every deploy; **no data is dropped**.
2. **Variables** (Settings → Variables):
   - `DATABASE_URL` → **Add Reference → Postgres → DATABASE_URL** (Railway's
     `postgres://` is auto-normalized to `postgresql://` in `database.py`).
   - `SECRET_KEY` → a long random string.
   - `ALLOWED_ORIGINS` → the frontend's public URL (set after step 3).
   - `ANTHROPIC_API_KEY` (AI assistant).
   - Optional email: `RESEND_API_KEY` + `FROM_EMAIL`, or `SMTP_*`.
   - Optional payments: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`.
3. **Settings → Networking → Generate Domain** → note the backend URL.

## 3. Frontend service

1. **+ New → GitHub Repo** (same repo) → **Settings**:
   - **Root Directory: `frontend`**  ← required.
   - Railway finds `frontend/Dockerfile`: it runs `npm run build` then
     `serve -s build -l $PORT`.
2. **Variables:**
   - `REACT_APP_API_BASE` → the backend's public URL from step 2
     (e.g. `https://sage-backend.up.railway.app`).
   - **Important:** CRA bakes `REACT_APP_*` at **build time**. The frontend
     Dockerfile declares `ARG REACT_APP_API_BASE`, and Railway passes the service
     variable in as a build arg. If you change this value, **redeploy** so the
     bundle is rebuilt.
3. **Generate Domain** for the frontend.
4. Back on the **backend** service, set `ALLOWED_ORIGINS` to the frontend domain
   and redeploy the backend (so CORS accepts it).

## 4. First sign-in

On first boot the backend seeds default accounts (`seed_defaults` in `main.py`):

- Owner — `owner@sage.school` / `owner123`
- Staff — `staff@sage.school` / `staff123`

**Change these passwords immediately** after first login.

---

## Database migrations (Alembic)

- Schema is versioned in `backend/migrations/`; `migrations/env.py` reads the
  same env-driven `DATABASE_URL` as the app (SQLite locally, Postgres on Railway).
- `alembic upgrade head` runs on every backend deploy (start command).
- After changing models:
  ```bash
  cd backend
  alembic revision --autogenerate -m "describe change"
  alembic upgrade head
  ```

## Local development

```bash
# Backend (SQLite, no env needed)
cd backend && pip install -r requirements.txt
uvicorn main:app --reload            # http://127.0.0.1:8000

# Frontend
cd frontend && npm install
npm start                            # http://localhost:3000 → talks to :8000
```

`docker-compose up` also runs both locally (backend :8000, frontend :3000).

## Troubleshooting

- **`Railpack could not determine how to build the app`** → Root Directory is the
  repo root. Set it to `backend` or `frontend` (see above). This is the cause of
  ~every first-time failure on this repo.
- **Frontend loads but API calls fail (CORS / network)** → `REACT_APP_API_BASE`
  wasn't set at build time, or `ALLOWED_ORIGINS` on the backend doesn't include
  the frontend domain. Fix the variable and redeploy the affected service.
- **502 on the backend right after deploy** → check the deploy logs for the
  `alembic upgrade head` step; a bad `DATABASE_URL` reference is the usual cause.

## Notes / tradeoffs

- **Single-service alternative:** to avoid two URLs + CORS, have FastAPI serve the
  built React assets and run one service. Simpler for a single school; the
  two-service split is cleaner for scaling.
- **Uploads** (assignment submissions) write to the backend container's
  **ephemeral** disk — they don't survive a redeploy. Attach a Railway **Volume**
  at `backend/uploads/` (or use object storage) for durable files. The database
  is safe on the Postgres plugin.
- **Web push** is staged (service-worker listeners exist); VAPID keys aren't wired
  yet — email notifications work today.
