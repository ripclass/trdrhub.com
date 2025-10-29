# API Specification

A REST API is the most pragmatic approach, as FastAPI natively generates the required OpenAPI specification.

- **POST /auth/register**: Register a new user.
- **POST /auth/login**: Log in and receive a JWT.
- **POST /sessions**: Create a new validation session and get pre-signed URLs for document uploads.
- **GET /sessions**: List all past validation sessions for the logged-in user.
- **GET /sessions/{sessionId}**: Get the status and results of a validation session.
- **GET /sessions/{sessionId}/report**: Get a pre-signed URL to download the final report PDF.
