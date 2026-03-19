# LCopilot Troubleshooting

This guide covers the beta-critical failures most likely to block LCopilot launch readiness.

## 1. Wrong dashboard after login

Check:

- `/auth/me` returns the expected normalized role
- `/onboarding/status` returns expected company and onboarding details
- the frontend is not still using a legacy auth context for the target dashboard

Symptom:

- exporter user lands in importer or another dashboard
- importer lands in exporter unexpectedly
- user sees a dashboard that does not match current onboarding truth

## 2. User identity bleed after logout/login

Check:

- local storage and session storage are actually cleared
- the surface is using the shared auth hook instead of a legacy context
- sidebar and dashboard read the same user source

Symptom:

- old user name appears after switching accounts
- UI shows mixed identity details

## 3. Validation runs but results page is contradictory

Check:

- `GET /api/results/{jobId}` returns `structured_result`
- `structured_result.version` is `structured_result_v1`
- frontend results mapping is rendering backend truth rather than fallback state

Symptom:

- overview counts differ from issues or documents
- verdict or readiness looks inconsistent
- key result surfaces disappear after refresh

## 4. Validation request fails

Check:

- backend is reachable
- auth is valid
- uploaded files and form fields are present
- `POST /api/validate` is receiving the correct `user_type` and `workflow_type`

Useful endpoints:

- `/docs`
- `/healthz`
- `/health/live`
- `/health/ready`

## 5. Results cannot be reopened

Check:

- the job id is valid
- the validation session exists
- persisted `structured_result` was written to the session
- `GET /api/results/{jobId}` returns the stored payload

## 6. Local build or test confusion

Use the beta-critical commands first:

```bash
npm run build
npm run test
cd apps/web && npm run test && npm run build
cd apps/api && pytest
```

If tests fail in old or non-beta surfaces, separate that from failures in the launch-critical exporter, importer, auth, or result-contract paths.
