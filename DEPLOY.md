# Deploying Sage to Railway

Sage deploys as **two services in one repo** (backend + frontend) plus a
**Postgres** plugin. The frontend talks to the backend over its public URL
(set at build time), so the two are independently deployable.

```
Railway project
├── Postgres        (plugin → provides DATABASE_URL)
├── backend         (root: backend/)   FastAPI + uvicorn
└── frontend        (root: frontend/)  CRA static build served by `serve`
```

Everything is env-driven — no code changes are needed to deploy. Configs live in
`backend/railway.json` (+ `Procfile`) and `frontend/railway.json`.

---

## 1. Create the project + Postgres

1. Push this repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo** → pick this repo.
3. **+ New → Database → Add PostgreSQL.** Railway exposes its connection string
   as `DATABASE_URL` on the Postgres service.

## 2. Backend service

1. **+ New → GitHub Repo** (same repo) → in the service **Settings**:
   - **Root Directory:** `backend`
   - Build/Start come from `backend/railway.json`:
     `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`
     (migrations run on every deploy; data is never dropped).
2. **Variables** (Settings → Variables):
   - `DATABASE_URL` → reference the Postgres service's `DATABASE_URL`
     (Railway: "Add Reference → Postgres → DATABASE_URL"). `postgres://` is
     auto-normalized to `postgresql://` in `database.py`.
   - `SECRET_KEY` → a long random string.
   - `ALLOWED_ORIGINS` → the frontend's public URL (fill in after step 3, e.g.
     `https://sage-frontend.up.railway.app`).
   - `ANTHROPIC_API_KEY` (for the AI assistant).
   - Optional email: `RESEND_API_KEY` + `FROM_EMAIL`, or `SMTP_*`.
   - Optional payments: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`.
3. Deploy. Under **Settings → Networking → Generate Domain** to get the public URL.

## 3. Frontend service

1. **+ New → GitHub Repo** (same repo) → **Settings**:
   - **Root Directory:** `frontend`
   - Build/Start come from `frontend/railway.json`: Nixpacks runs `npm run build`,
     then `npx serve -s build -l $PORT`.
2. **Variables:**
   - `REACT_APP_API_BASE` → the backend's public URL from step 2
     (e.g. `https://sage-backend.up.railway.app`). **CRA reads `REACT_APP_*` at
     build time**, so set this before the build and redeploy if you change it.
3. **Generate Domain** for the frontend.
4. Go back to the **backend** service and set `ALLOWED_ORIGINS` to this frontend
   domain, then redeploy the backend.

## 4. First sign-in

On first boot the backend seeds default accounts (see `seed_defaults` in
`main.py`):

- Owner — `owner@sage.school` / `owner123`
- Staff — `staff@sage.school` / `staff123`

**Change these passwords immediately** after first login.

---

## Database migrations (Alembic)

- The schema is versioned with Alembic under `backend/migrations/`.
- `alembic upgrade head` runs automatically on each backend deploy (start command).
- Create a new migration after changing models:
  ```bash
  cd backend
  alembic revision --autogenerate -m "describe change"
  alembic upgrade head
  ```
- `migrations/env.py` reads the same env-driven `DATABASE_URL` as the app, so it
  targets SQLite locally and Postgres in production automatically.

## Local development

```bash
# Backend (SQLite, no env needed)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload         # http://127.0.0.1:8000

# Frontend
cd frontend
npm install
npm start                          # http://localhost:3000  → talks to :8000
```

`docker-compose.yml` also runs both services locally (backend on 8000, frontend
on 80 via nginx).

## Notes / tradeoffs

- **Two services vs. one:** two URLs + CORS, but clean separation and independent
  scaling. To run as a single service instead, have FastAPI serve the built React
  assets and drop the frontend service (simpler, fine for one school).
- **Uploads** (assignment submissions) are written to the backend container's
  disk, which is **ephemeral** on Railway — they don't survive a redeploy. Attach
  a Railway **Volume** mounted at `backend/uploads/`, or switch to object storage,
  for durable file submissions. The database itself is safe on the Postgres plugin.
- **Web push** is staged (the service worker has the listeners) but VAPID keys
  are not wired yet — email notifications work today.
