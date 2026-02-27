# TRDR Hub

**Enterprise-grade trade compliance tools for SME exporters, trade banks, and compliance teams.**

TRDR Hub provides a suite of AI-powered tools to validate Letters of Credit, verify commodity prices, track shipments, and ensure trade compliance - all powered by 4,000+ rules covering UCP600, ISBP745, and 160+ countries.

**Production:** https://trdrhub.com  
**API:** https://trdrhub-api.onrender.com

---

## 🚀 Live Tools

| Tool | Description | Status |
|------|-------------|--------|
| **LCopilot** | AI-assisted LC validation with UCP600/ISBP rules | ✅ Live |
| **Price Verify** | Commodity price verification for TBML detection | ✅ Live |
| **Container Tracker** | Multi-carrier shipment tracking with alerts | ✅ Live |

---

## Repository Layout

```
trdrhub.com/
├── apps/
│   ├── api/            # FastAPI backend (Python 3.11)
│   └── web/            # React + Vite frontend (TypeScript)
├── Data/               # Trade finance rules (4,000+ rulesets)
│   ├── icc_core/       # UCP600, ISBP745, eUCP
│   ├── country_rules/  # 160+ country-specific rules
│   ├── sanctions/      # OFAC, EU, UN sanctions data
│   └── commodities/    # Commodity pricing data
├── docs/               # Product, architecture, and process documentation
├── memory-bank/        # AI context persistence
├── packages/
│   └── shared-types/   # Shared TypeScript/Python types
├── render.yaml         # Render deployment (API)
└── vercel.json         # Vercel deployment (Web)
```

---

## Technology Stack

| Area | Tech |
|------|------|
| **Frontend** | React 18 + Vite + TypeScript + Tailwind + shadcn/ui |
| **Backend** | FastAPI + SQLAlchemy + Alembic + Pydantic |
| **Database** | PostgreSQL (Supabase) |
| **Auth** | Supabase Auth + JWT + RBAC |
| **OCR / AI** | Google Document AI, AWS Textract, OpenAI/Anthropic |
| **Storage** | Amazon S3 |
| **Monitoring** | Structured logging, health checks |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 18+ (npm 10+)
- PostgreSQL 15
- (Optional) Redis for background tasks

### 2. Install Dependencies

```bash
git clone https://github.com/ripclass/trdrhub.com.git
cd trdrhub.com

# Root workspace
npm install

# Backend
cd apps/api
pip install -r requirements.txt

# Frontend
cd ../web
npm install
```

### 3. Configure Environment

```bash
# Copy templates
cp .env.example .env
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
```

Key variables:
- `DATABASE_URL` – PostgreSQL connection
- `VITE_API_URL` – API endpoint for frontend
- `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` – Supabase auth
- `GOOGLE_DOCUMENTAI_*` – OCR credentials
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` – AI assist

### 4. Database Setup

```bash
cd apps/api
alembic upgrade head
```

### 5. Run Locally

```bash
# Backend (terminal 1)
cd apps/api
uvicorn main:app --reload --port 8000

# Frontend (terminal 2)
cd apps/web
npm run dev
```

- Backend: http://localhost:8000/docs
- Frontend: http://localhost:5173

---

## Deployment

### Backend (Render)

```bash
render blueprint deploy
```

- Uses `render.yaml` configuration
- Auto-runs Alembic migrations on deploy
- Health check: `/health/live`

### Frontend (Vercel)

```bash
vercel --prod
```

- Uses `vercel.json` configuration
- Set `VITE_API_URL` environment variable

---

## Documentation

| Document | Location |
|----------|----------|
| **Current Status** | `docs/CURRENT_STATUS.md` |
| **Product Requirements** | `docs/prd/index.md` |
| **Architecture** | `docs/architecture/index.md` |
| **Product Specs** | `docs/product_specs/` |
| **Compliance Mappings** | `docs/compliance/` |
| **Runbooks** | `docs/runbooks/` |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Total Rules | 4,000+ |
| Countries Covered | 160+ |
| LC Validation Accuracy | 94% |
| Processing Time | ~47 seconds |

---

## Testing

```bash
# Backend tests
cd apps/api && pytest

# Frontend build check
cd apps/web && npm run build

# Migration check
cd apps/api && alembic check
```

## Day-3 Local Automation (Paste folders -> run 1 command)

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\day3_pipeline\run_day3.ps1
```

Detailed quickstart: `tools/day3_pipeline/README_DAY3_AUTOPILOT.md`

---

## Support

- **Documentation:** `docs/` directory
- **Troubleshooting:** `TROUBLESHOOTING.md`
- **Stub Mode:** `STUB_MODE.md` (for local dev without cloud services)

---

*Built with ❤️ for trade finance professionals*
