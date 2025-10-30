# TRDR Hub LCopilot

AI-assisted Letter of Credit validation for SME exporters, trade banks, and compliance teams.

This monorepo contains the FastAPI backend and the Vite/React frontend that power LCopilot. The backend handles document intake, OCR, rule-based validation, AI assist flows, billing, and analytics. The frontend delivers the operator experience, dashboards, and customer-facing workflows.

---

## Repository Layout

```
trdrhub.com/
├── apps/
│   ├── api/     # FastAPI service (Python 3.11)
│   └── web/     # React + Vite frontend (TypeScript)
├── docs/        # Product, architecture, and process documentation
├── render.yaml  # Render deployment configuration for api
└── vercel.json  # Vercel deployment configuration for web
```

The project uses npm workspaces (Turborepo) to coordinate shared tooling and scripts.

---

## Technology Stack

| Area        | Tech                                  |
|-------------|---------------------------------------|
| Backend     | FastAPI, SQLAlchemy, Alembic, Pydantic |
| Database    | PostgreSQL (Supabase compatible)       |
| Storage     | Amazon S3 (stub mode for local dev)    |
| OCR / AI    | Google Document AI, AWS Textract, OpenAI/Anthropic (optional) |
| Frontend    | React 18 + Vite + Tailwind/ShadCN      |
| Auth        | JWT with role-based access             |
| Monitoring  | AWS CloudWatch, structured logging     |

---

## Quick Start

### 1. Install prerequisites

- Python 3.11+
- Node.js 18+ (npm 10+)
- PostgreSQL 15
- (Optional) Redis for background tasks

### 2. Install dependencies

```bash
git clone https://github.com/ripclass/trdrhub.com.git
cd trdrhub.com

# Install root workspace dependencies
npm install

# Install backend dependencies
cd apps/api
pip install -r requirements.txt

# Install frontend dependencies
cd ../web
npm install
```

### 3. Configure environment variables

Templates ship with all required keys. Copy and customise the ones you need:

```
# Root configuration (used by FastAPI Settings)
cp .env.example .env

# Backend (apps/api)
cp apps/api/.env.example apps/api/.env

# Frontend (apps/web)
cp apps/web/.env.example apps/web/.env
```

> :warning: Populate secrets such as `DATABASE_URL`, `JWT_SECRET_KEY`, `OPENAI_API_KEY`, and payment provider keys before running in non-stub mode. Production defaults live in `.env.production.template`.

### 4. Prepare the database

```bash
createdb lcopilot_dev
cd apps/api
alembic upgrade head
```

### 5. Run services locally

```bash
# Backend
cd apps/api
uvicorn main:app --reload

# Frontend (new shell)
cd apps/web
npm run dev
```

Backend health endpoints:
- `http://localhost:8000/health/live`
- `http://localhost:8000/docs`

Frontend dev server: `http://localhost:5173`

---

## Testing & Quality Checks

| Command | Description |
|---------|-------------|
| `cd apps/api && pytest` | Backend test suite (unit, integration, security) |
| `cd apps/api && alembic check` | Validate Alembic migration chain |
| `cd apps/web && npm run build` | Build-time smoke test for the frontend |

> Run `pytest` before deploying. The test runner expects environment variables from `apps/api/.env`.

---

## Deployment

### Backend (Render)

- `render.yaml` provisions a Python web service using `apps/api` as the root.
- Build command installs requirements, `postDeployCommand` runs Alembic migrations.
- Health check is wired to `/health/live`.

Deploy with:

```bash
render blueprint deploy
```

Map secrets via Render Environment Groups to populate the variables in `.env.production.template`.

### Frontend (Vercel)

- `vercel.json` builds the Vite application in `apps/web`.
- Set `VITE_API_URL` to the public API URL and `VITE_TOKEN_STORAGE_KEY` if you change the storage key.

Deploy with:

```bash
vercel --prod
```

---

## Environment Reference

Key templates:

- Root: `.env.example`, `.env.production.template`
- Backend: `apps/api/.env.example`, `apps/api/.env.production.template`
- Frontend: `apps/web/.env.example`, `apps/web/.env.production.template`

Important variables:

- `DATABASE_URL` – PostgreSQL connection string
- `JWT_SECRET_KEY` / `JWT_EXPIRATION_HOURS`
- `AWS_REGION`, `S3_BUCKET_NAME`, `DR_OBJECT_BACKUP_BUCKET`
- `GOOGLE_DOCUMENTAI_*` for OCR
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LLM_MODEL_VERSION`
- Billing providers: `STRIPE_*`, `SSLCOMMERZ_*`
- Frontend: `VITE_API_URL`, `VITE_TOKEN_STORAGE_KEY`

---

## Documentation & Support

- Product requirements: `docs/prd/index.md`
- Architecture reference: `docs/architecture/index.md`
- Monitoring & operations: `apps/api/MONITORING.md`, `apps/api/audit_monitoring.crontab`
- Troubleshooting: `TROUBLESHOOTING.md`, `STUB_MODE.md`

For further questions, check the detailed guides under `docs/` or reach out to the platform team.
