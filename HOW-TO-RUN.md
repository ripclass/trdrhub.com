# How to Run TRDR Hub Locally

This guide walks through spinning up the LCopilot backend and frontend on a developer workstation.

---

## 1. Prerequisites

- **Python 3.11+**
- **Node.js 18+** (npm 10+)
- **PostgreSQL 15** running locally or via Docker
- (Optional) **Redis** for background tasks
- Google DocAI / AWS credentials if you plan to leave stub mode

---

## 2. Install Dependencies

```bash
git clone https://github.com/ripclass/trdrhub.com.git
cd trdrhub.com

# Root workspace deps
npm install

# Backend deps
cd apps/api
pip install -r requirements.txt

# Frontend deps
cd ../web
npm install
```

---

## 3. Configure Environment Variables

Templates include all required keys. Copy and edit as needed:

```bash
cp .env.example .env
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
```

Key values to update:

- `DATABASE_URL` (PostgreSQL)
- `SECRET_KEY` / `JWT_SECRET_KEY`
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` (optional AI assist)
- `STRIPE_*`, `SSLCOMMERZ_*` and URLs for billing callbacks
- `VITE_API_URL` (defaults to `http://localhost:8000`)

To enable live cloud services, set `USE_STUBS=false` and provide AWS/GCP credentials (`S3_BUCKET_NAME`, `GOOGLE_DOCUMENTAI_*`).

---

## 4. Prepare the Database

```bash
createdb lcopilot_dev
cd apps/api
alembic upgrade head
```

This applies the schema defined in `apps/api/alembic/versions`.

---

## 5. Run the Backend

```bash
cd apps/api
uvicorn main:app --reload
```

Key endpoints:

- API root: `http://localhost:8000/`
- OpenAPI docs: `http://localhost:8000/docs`
- Health checks: `/health/live`, `/health/ready`

Stub mode (default) uses local storage under `apps/api/stubs`.

---

## 6. Run the Frontend

```bash
cd apps/web
npm run dev
```

Visit `http://localhost:5173`. The app automatically calls the backend using `VITE_API_URL`.

The new Axios client lives in `src/api/client.ts` and injects JWT tokens stored under `VITE_TOKEN_STORAGE_KEY` (default `lcopilot_token`).

---

## 7. Run Tests

| Area      | Command                     |
|-----------|-----------------------------|
| Backend   | `cd apps/api && pytest`     |
| Frontend  | `cd apps/web && npm run build` (smoke) |
| Migrations | `cd apps/api && alembic check` |

Ensure tests pass before opening a pull request or deploying.

---

## 8. Deployment Cheatsheet

- **Render (API):** `render.yaml` configures build/start commands and automatically runs `alembic upgrade head`.
- **Vercel (Web):** `vercel.json` builds the Vite app from `apps/web`. Set `VITE_API_URL` to the Render URL.

For production, set `ENVIRONMENT=production`, point to managed Postgres/S3, and disable stub mode.

---

## Troubleshooting

- Missing tables? Re-run `alembic upgrade head`.
- DocAI errors? Confirm `GOOGLE_APPLICATION_CREDENTIALS` and project/processor IDs.
- Billing endpoints returning 401? Verify JWT secret consistency (`JWT_SECRET_KEY`) across API and frontend.
- Unexpected UI crash? The global error boundary surfaces the error and you can reload from the fallback screen.

Refer to `TROUBLESHOOTING.md` and `apps/api/MONITORING.md` for deeper diagnostics.
