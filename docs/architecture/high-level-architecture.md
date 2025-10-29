# High-Level Architecture

## Technical Summary

The architecture will be a serverless fullstack application in a monorepo. The frontend will be a React Single-Page Application (SPA) hosted on Vercel. The backend will be a monolithic FastAPI (Python) service deployed as a serverless function on AWS. An asynchronous, queue-based processing model will be used for long-running tasks like OCR to ensure API responsiveness. This approach prioritizes rapid development, low operational overhead, and scalability.

## Platform and Infrastructure Choice

**Platform**: A combination of Vercel for the frontend and AWS for the backend.

**Key Services:**
- **Vercel**: Hosting, CI/CD, and CDN for the React frontend.
- **AWS Lambda + API Gateway**: For hosting the serverless FastAPI backend.
- **Amazon S3**: For direct, secure file uploads and report storage.
- **Amazon SQS**: For decoupling the API from the asynchronous worker.
- **Amazon RDS (PostgreSQL)**: For the managed relational database.

## High-Level Architecture Diagram

This diagram shows the asynchronous flow, which solves file size limits and timeouts by keeping the API thin and fast.

```mermaid
graph TD
    A[User (SPA on Vercel)] -->|Auth + UI| B[Vercel CDN]
    B --> C[React SPA]
    C -->|GET pre-signed URL| D[API Gateway]
    D --> E[Lambda: FastAPI API]
    C -->|PUT file| S3[(S3 Uploads - KMS)]
    E -->|Enqueue job meta| Q[(SQS Jobs)]
    W[Worker (Lambda or ECS Fargate)]
    Q --> W
    W -->|Get file| S3
    W -->|OCR DocAI/Textract| O[[OCR Vendors]]
    W -->|Rules Engine + Report| RDS[(Amazon RDS Postgres)]
    W -->|Write PDF| SP[(S3 Reports - KMS)]
    C -->|Poll/WS for status| E
    E -->|Return report link| C
```
