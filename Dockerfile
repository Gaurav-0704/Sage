# Single-service image: build the React app, then serve it from FastAPI under /.
# This is the simplest Railway deploy — one service, no CORS, no second URL.
# Deploy the repo with the default Root Directory and Railway uses this file.

# 1) Build the static frontend (API base is same-origin /api).
FROM node:20-alpine AS fe
WORKDIR /fe
COPY frontend/package*.json ./
# --legacy-peer-deps: React 19 + react-scripts 5 have a peer-dep mismatch that
# trips npm's strict resolver; this is the standard CRA workaround.
RUN npm ci --legacy-peer-deps --no-audit --no-fund
COPY frontend/ ./
ENV REACT_APP_API_BASE=/api
RUN npm run build

# 2) Backend image that also serves the build.
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=fe /fe/build ./frontend_build
ENV FRONTEND_BUILD_DIR=/app/frontend_build
# Fresh deploys are clean (only the owner/staff logins are seeded). To populate
# sample students/teachers/marks for a demo, set SEED_DEMO=true on the service.
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
