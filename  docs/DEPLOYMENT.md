# LCopilot Deployment Guide

This document captures the minimum steps required to run the LCopilot stack locally and promote it to the hosted environments (Render for the API, Vercel for the UI).

## 1. Environment Variables

Use the repo level `.env.example` as the source of truth. Copy it to `.env` (or per-service `.env` files) and fill in:

- `DATABASE_URL` – Postgres/Supabase connection string.
- `SECRET_KEY` – FastAPI session/JWT secret.
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWKS_URL` – Supabase Auth.
- `GOOGLE_*` – Document AI configuration (or set `USE_DEEPSEEK_OCR=true` and configure DeepSeek).
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` – Optional LLM providers.
- Frontend values (`VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, etc.).

## 2. Running Locally

```bash
# Backend
cd apps/api
cp env.example .env  # fill in secrets
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload

# Frontend
cd apps/web
npm install
cp .env.example .env
npm run dev
```

API health check: `curl http://localhost:8000/healthz`  
UI served at: `http://localhost:5173`

## 3. Deploying the Backend (Render)

- Render reads `render.yaml`:
  - Builds with `pip install -r requirements.txt`
  - Runs migrations via `alembic upgrade head`
  - Starts `uvicorn main:app --host 0.0.0.0 --port $PORT`
  - Health probe: `GET /healthz`
- Configure secrets inside the Render dashboard or via environment groups (match `.env.example` keys).

## 4. Deploying the Frontend (Vercel)

- `apps/web/vercel.json` instructs Vercel to:
  - Install dependencies (`npm install`)
  - Run `npm run build`
  - Serve from `apps/web/dist`
  - Proxy `/api/*` to the Render API
- Set the VITE_* variables inside the Vercel project settings (they are baked into the build).

## 5. Continuous Integration

`.github/workflows/ci.yml` runs on push/PR:

1. **Backend job** – installs Python deps, runs lint, type check, pytest suites.
2. **Frontend job** – installs Node deps, runs lint, `npm run type-check`, `npm run test`, and `npm run build`.
3. Additional jobs (E2E, security scans, container builds) run on the appropriate branches and gate deployments.

## 6. Observability

- `/healthz` – lightweight probe for load balancers (returns `{ "status": "ok" }`).
- `/health/live` and `/health/ready` – detailed health/readiness checks.
- Logs: Uvicorn/FastAPI logs are emitted to stdout; Render/Vercel ingest them automatically.
