# How to Run LCopilot Locally

This guide focuses on the beta-critical LCopilot surfaces in the monorepo.

## 1. Install dependencies

```bash
npm install

cd apps/api
pip install -r requirements.txt

cd ../web
npm install
```

## 2. Configure environment

Copy the repo templates and fill in the values you need:

```bash
cp .env.example .env
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
```

For local beta-focused work, the important values are:

- database connection
- Supabase auth values
- `VITE_API_URL`
- OCR and storage credentials if you want non-stub validation

## 3. Prepare the database

```bash
cd apps/api
alembic upgrade head
```

## 4. Start the backend

```bash
cd apps/api
uvicorn main:app --reload
```

Useful checks:

- `http://localhost:8000/docs`
- `http://localhost:8000/healthz`
- `http://localhost:8000/health/live`
- `http://localhost:8000/health/ready`

## 5. Start the frontend

```bash
cd apps/web
npm run dev
```

Primary beta pages to exercise:

- `/login`
- `/lcopilot/exporter-dashboard`
- `/lcopilot/importer-dashboard`

## 6. Useful local tests

```bash
npm run build
npm run test

cd apps/web && npm run test && npm run build
cd apps/api && pytest
```

## 7. What to verify first

For beta-critical local work, verify this order:

1. login and logout
2. dashboard routing
3. exporter upload and results
4. importer upload and results
5. history and reopen path
6. quota or paywall behavior

If a change does not improve one of those loops, it is probably not first-priority beta work.
