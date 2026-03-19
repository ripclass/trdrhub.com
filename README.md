# TRDR Hub Monorepo

LCopilot is the primary ship target in this repository. The current sprint is preparing the LCopilot Public Beta, not a broad multi-product launch.

## LCopilot Public Beta

- Exporter is the gold path and the deepest surface in the repo today.
- Importer is a real beta journey, but it must converge onto the same auth, validation, and result spine as exporter.
- Bank exists in the codebase but is parked from launch-critical scope for this beta.
- The strongest asset is the validation core.
- The biggest blocker is auth, onboarding, and routing trust.
- The canonical result truth is persisted `structured_result` served by `GET /api/results/{jobId}`.
- The frontend must render from that payload and must not fabricate contradictory state.
- Beta assumptions: public beta, English only, hard paywall with an initial free-check or free-token allowance.

## Product Truth

- `POST /api/validate` is the canonical validation entrypoint.
- Validation results are persisted on the backend and served again through `GET /api/results/{jobId}`.
- `structured_result` is the canonical backend contract for exporter and importer review pages.
- Exporter and importer should share the same backend payload, shared types, and frontend result-mapping spine.

## Monorepo Layout

| Path | Purpose |
| --- | --- |
| `apps/api` | FastAPI backend: auth, onboarding, validation pipeline, result persistence, result serving |
| `apps/web` | React + Vite frontend: login, dashboards, upload flows, results pages |
| `packages/shared-types` | Shared TypeScript and Python types, including LCopilot result schemas |
| `docs` | Canonical beta docs plus supporting historical references |

## Canonical Docs

| Topic | Canonical doc |
| --- | --- |
| Current beta truth | `docs/CURRENT_STATUS.md` |
| Product brief | `docs/brief/index.md` |
| Architecture | `docs/architecture/index.md` |
| Auth, onboarding, routing | `docs/AUTH_ONBOARDING_ROUTING_CURRENT_STATE.md` |
| Local development | `HOW-TO-RUN.md` |
| Deployment and release | `docs/DEPLOYMENT.md` |

## Quick Start

```bash
npm install

cd apps/api
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload

cd ../web
npm install
npm run dev
```

Useful endpoints:

- API docs: `http://localhost:8000/docs`
- Health: `/healthz`, `/health/live`, `/health/ready`
- Frontend: `http://localhost:5173`

## Build and Test

```bash
npm run build
npm run test

cd apps/api && pytest
cd apps/web && npm run test && npm run build
```

Note:

- Some older docs in the repo describe broader platform ambitions or historical launch tracks. Use the canonical docs above for the current LCopilot beta truth.
- Other TRDR Hub tools remain in the repository, but they are secondary to this LCopilot beta sprint.
