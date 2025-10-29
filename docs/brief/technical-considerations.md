# Technical Considerations

## Technology Preferences

- **Backend**: FastAPI (Python)
- **Frontend**: React
- **Core Technology**: OCR + LLM-supplemented Rules Engine
- **Language Support**: English + Bangla

## ⚠️ Small Risks & Guardrails

- **Concurrency bottlenecks (FastAPI + Python)**: fine for 1k SMEs, but under 10k+ concurrent checks → add async workers.
- **OCR costs**: could eat margins at high scale → hybrid OCR strategy later.
- **LLM dependency (cost + API reliance)**: fine for MVP, but OSS plan is critical for sustainability.
- **SME UX**: must be ultra-simple → resist feature creep before nailing upload → report flow.
