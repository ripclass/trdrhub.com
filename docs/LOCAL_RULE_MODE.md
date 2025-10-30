# Local Rule Mode (Standalone Rules Registry)

## Purpose

Enable LC validation without RulHub by storing ICC rules locally in Postgres (`rules_registry`) and using the validator service to evaluate documents.

## Setup Steps

1. Run DB migration (inside `apps/api`):

```bash
cd apps/api
alembic upgrade head
```

2. Seed initial ICC rules (from project root):

```bash
python scripts/seed_rules.py
```

3. Start API:

```bash
cd apps/api
uvicorn main:app --reload
```

## API Usage

POST `http://localhost:8000/api/validate/`

Example payloads:

```json
{"document_type":"lc","consistency":true}
```

```json
{"document_type":"invoice","date_format":"15/10/2025"}
```

Example response:

```json
{
  "status": "ok",
  "results": [
    {"rule": "UCP600-14(a)", "title": "Consistency of Data", "passed": true, "severity": "fail", "message": "All data consistent with LC"}
  ]
}
```

## Data Model

Table: `rules_registry`

- `id` UUID (default: `gen_random_uuid()`)
- `code` (e.g., `UCP600-14(a)`)
- `title`, `description`
- `condition` JSONB: `{ "field": str, "operator": "equals|matches", "value": any }`
- `expected_outcome` JSONB: e.g., `{ "message": "Valid date format" }`
- `domain` (e.g., `icc`), `jurisdiction` (default `global`)
- `document_type` (e.g., `lc`, `invoice`)
- `version` (default `UCP600:2007`)
- `severity` (default `fail`)
- timestamps

## Operators

- `equals`: strict equality against `payload[field]`
- `matches`: regex against `str(payload[field])`

## Migration Path to RulHub

- Schema mirrors core RulHub fields for forward compatibility
- To migrate later, sync rules from RulHub into `rules_registry` or switch validator service to fetch remotely
- Keep `code` stable; treat it as external rule identifier

## Notes

- Migration enables `pgcrypto` for `gen_random_uuid()`
- Seed script adds minimal ICC samples; extend as needed
- Router is mounted at `/api/validate` for curl compatibility
