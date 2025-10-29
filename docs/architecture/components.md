# Components

The architecture is composed of six primary logical components with a clear separation of concerns.

- **Frontend SPA (React)**: Handles all user interaction.
- **Backend API (FastAPI)**: Acts as the thin, synchronous control plane for auth and session management.
- **Validation Worker (Lambda/Fargate)**: The asynchronous workhorse for OCR, rules, and report generation.
- **Database (PostgreSQL/RDS)**: The single source of truth for all persistent state.
- **Storage Service (S3)**: Provides secure storage for uploads and reports.
- **Queue Service (SQS)**: Decouples the API from the long-running worker.
