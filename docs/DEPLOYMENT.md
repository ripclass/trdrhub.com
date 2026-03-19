# LCopilot Deployment Guide

This guide covers the beta-critical deployment path for LCopilot.

## Deployment targets

### Backend

- platform: Render
- config: `render.yaml`
- root dir: `apps/api`
- build command: `pip install --upgrade pip && pip install -r requirements.txt`
- start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- post-deploy migration: `alembic upgrade head`
- health check path: `/healthz`

### Frontend

- platform: Vercel
- config: `vercel.json`
- build command: `cd apps/web && npm install && npm run build`
- output directory: `apps/web/dist`

## Required environment truth

Minimum launch-critical configuration:

- database connection
- Supabase auth values
- API and frontend environment values
- OCR provider credentials for non-stub operation
- storage configuration
- billing and quota configuration

## Health endpoints

- `/healthz` - lightweight deploy health check
- `/health/live` - liveness
- `/health/ready` - readiness

## Beta release checks

A deployment is not beta-ready unless the following work on the deployed environment:

- `/auth/me`
- `/onboarding/status`
- `POST /api/validate`
- `GET /api/results/{jobId}`
- exporter dashboard flow
- importer dashboard flow
- quota or paywall enforcement path

## Release discipline

Before promoting a release:

1. run frontend tests and build
2. run backend tests that cover launch-critical flows
3. verify migrations
4. run manual smoke checks on auth, validation, results, history, and gating

Bank-specific deployment checks are not part of the LCopilot public beta gate.
