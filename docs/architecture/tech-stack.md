# Tech Stack

This table outlines the specific technologies and the known risks or "guardrails" for each choice.

| Category | Technology | Version | Risks & Mitigations (Guardrails) |
|----------|------------|---------|-----------------------------------|
| Monorepo Tool | Turborepo | latest | Risk: Devs unfamiliar with config. Mitigation: Keep config minimal; add README with common commands. |
| Frontend Framework | React | 18.x | Risk: Less suited for SEO than Next.js. Mitigation: MVP is a tool, not a content site; this is acceptable. |
| Backend Framework | FastAPI (Python) | latest | Risk: Cold starts. Mitigation: Keep Lambda app small; move heavy compute to async workers. |
| Database | PostgreSQL | 15.x | Risk: Connection exhaustion from Lambdas. Mitigation: Use RDS Proxy from day one. |
| File Storage | Amazon S3 | N/A | Risk: Large file uploads. Mitigation: Enforce client-side size validation; use direct-to-S3 pre-signed URLs. |
| Async Messaging | Amazon SQS | N/A | Risk: Misconfigured timeouts causing job re-runs. Mitigation: Set timeouts longer than max OCR run; use idempotency keys. |
| Styling | Tailwind CSS | latest | Risk: Bangla font rendering issues. Mitigation: Ship a custom Unicode-safe font stack; test Bangla UI thoroughly. |
| PDF Generation | WeasyPrint | latest | Risk: Complex layouts may render differently. Mitigation: Build a canonical report.css; use screenshot tests in CI. |
| E2E Testing | Playwright | latest | Risk: Slow CI runs. Mitigation: Restrict to critical path smoke tests for the MVP. |
