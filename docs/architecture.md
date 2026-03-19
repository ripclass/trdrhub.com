# LCopilot Architecture Summary

This top-level file is a short pointer to the canonical architecture docs in `docs/architecture/`.

## Current beta architecture truth

- LCopilot ships as one shared validation and results spine.
- Exporter is the gold path.
- Importer must converge onto the same auth, validation, and result flow.
- Bank is parked from launch-critical scope.
- The validation core is the strongest part of the system.
- Auth, onboarding, and routing trust are the largest architectural risk.
- `structured_result` plus `GET /api/results/{jobId}` define the canonical result path for the web app.

Use `docs/architecture/index.md` for the canonical architecture set.
