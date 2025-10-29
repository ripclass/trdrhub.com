# Architecture Document v5: TRDR Hub LCopilot
## Bank-Grade Letter of Credit Validation Platform

**Version:** 5.0
**Date:** 2025-09-18
**Status:** Retrofitted to Current Implementation
**Owner:** Technical Architecture Team

## Executive Summary

This architecture document reflects the current implementation of TRDR Hub LCopilot as a bank-grade Letter of Credit validation platform. The system has evolved from a simple MVP to a comprehensive solution featuring multi-tenant isolation, immutable audit trails, disaster recovery automation, and enterprise-ready infrastructure.

### Architecture Principles

1. **Security by Design:** Bank-grade security controls built into every layer
2. **Multi-Tenant Isolation:** Secure tenant boundaries with RBAC enforcement
3. **Audit-First:** Immutable audit trails for regulatory compliance
4. **Cloud-Native:** Serverless and containerized components for scalability
5. **API-First:** Integration-ready design for bank system connectivity

## Document Structure

This architecture is sharded for BMAD workflow compatibility:

1. [Context & Constraints](./architecture/1-context-and-constraints.md)
2. [Components & Data Flow](./architecture/2-components-and-dataflow.md)
3. [Sequence Diagrams](./architecture/3-sequence-diagrams.md)
4. [Infrastructure & Deployment](./architecture/4-infra-and-deploy.md)
5. [Security & Compliance](./architecture/5-security-and-compliance.md)
6. [Observability & Disaster Recovery](./architecture/6-observability-and-dr.md)
7. [Failure Modes & Limits](./architecture/7-failure-modes-and-limits.md)

## High-Level Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web App       │    │   API Gateway    │    │  FastAPI Core   │
│   (React PWA)   │◄──►│   (AWS ALB)      │◄──►│  (Multi-Tenant) │
│   Multi-Language│    │   Rate Limiting  │    │  Auth + RBAC    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
        ┌────────────────────────────────────────────────┼─────────────────┐
        │                                                │                 │
        ▼                                                ▼                 ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   OCR Service   │    │  Rules Engine    │    │  Audit Service  │
│ (Google DocAI)  │    │ (Deterministic)  │    │ (Hash-Chained)  │
│ + File Storage  │    │ UCP600 + ISBP    │    │ Immutable Logs  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   Redis Cache    │    │  S3 Storage     │
│   Multi-Tenant  │    │   Session Store  │    │  Encrypted      │
│   Row-Level Sec │    │   Rate Limiting  │    │  Lifecycle Mgmt │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Current Implementation Status

### ✅ Implemented Components
- **FastAPI Backend:** Multi-tenant API with JWT authentication
- **React PWA Frontend:** Responsive design with i18n framework
- **PostgreSQL Database:** Multi-tenant with row-level security
- **OCR Pipeline:** Google DocumentAI integration
- **Rules Engine:** Deterministic UCP600 validation (60% coverage)
- **Audit System:** Hash-chained immutable audit trails
- **Security:** Encryption at rest/transit, secrets management
- **Infrastructure:** AWS deployment with IaC (CDK)
- **Monitoring:** Structured logging, health checks, metrics
- **DR System:** Automated backup/restore with RPO/RTO tracking

### ⚠️ Partially Implemented
- **Bank Integration:** IP whitelisting, mTLS framework (pilot-ready)
- **Queue System:** Basic Celery implementation (needs Redis/RabbitMQ)
- **Object Storage:** Local filesystem (needs S3/MinIO migration)
- **Database Pooling:** Direct connections (needs pgBouncer)

### 🚧 Planned Components
- **AI Validation:** LLM integration for complex scenario handling
- **Bank APIs:** SWIFT MT700/707/999 message processing
- **eUCP 2.1:** Electronic presentation support
- **Advanced Analytics:** Business intelligence dashboards

## Technology Stack

### Backend
- **Framework:** FastAPI 0.104.1 (Python 3.11+)
- **Database:** PostgreSQL 15+ with asyncpg driver
- **Authentication:** JWT with passlib bcrypt
- **Documentation:** Google DocumentAI 2.27.0
- **Task Queue:** Celery 5.3.4 with Redis backend
- **Monitoring:** Structlog 24.1.0 + CloudWatch

### Frontend
- **Framework:** React 18+ with TypeScript
- **Build Tool:** Vite with Turborepo monorepo
- **Styling:** Tailwind CSS with responsive design
- **PWA:** Service worker with offline capabilities
- **i18n:** React-i18next for Bangla/English support

### Infrastructure
- **Cloud:** AWS with multi-region deployment
- **Deployment:** AWS Lambda + API Gateway (serverless)
- **Database:** Amazon RDS PostgreSQL with read replicas
- **Storage:** Amazon S3 with KMS encryption
- **Monitoring:** CloudWatch + X-Ray tracing
- **Secrets:** AWS Secrets Manager with rotation

### Security
- **Encryption:** AES-256 at rest, TLS 1.3 in transit
- **Authentication:** JWT + OAuth2 with refresh tokens
- **Authorization:** Role-based access control (RBAC)
- **Audit:** Immutable hash-chained audit logs
- **Network:** VPC with private subnets, NACLs, security groups

## Integration Points

### External Services
- **Google DocumentAI:** OCR and document processing
- **AWS Services:** Lambda, RDS, S3, Secrets Manager, CloudWatch
- **Bank APIs:** SWIFT messaging (planned)
- **AI Providers:** OpenAI/Anthropic Claude (planned)

### Internal APIs
- **Authentication API:** JWT token management
- **Document API:** Upload, processing, validation
- **Rules API:** UCP600 compliance checking
- **Audit API:** Immutable trail management
- **Admin API:** Multi-tenant management, monitoring

## Data Architecture

### Multi-Tenant Design
- **Tenant Isolation:** Row-level security (RLS) in PostgreSQL
- **Data Partitioning:** Tenant-specific schemas for sensitive data
- **Access Control:** JWT claims with tenant context
- **Audit Separation:** Tenant-isolated audit trails

### Data Flow
1. **Document Upload:** Frontend → API Gateway → FastAPI → S3
2. **OCR Processing:** Async queue → Google DocumentAI → Database
3. **Rules Validation:** Document data → Rules engine → Results storage
4. **Audit Logging:** All actions → Hash-chained audit table
5. **Report Generation:** Validation results → PDF → S3 → Download link

## Deployment Architecture

### Environment Strategy
- **Local:** Docker Compose with PostgreSQL, Redis, MinIO
- **Staging:** AWS with reduced capacity, same architecture as production
- **Production:** Multi-AZ deployment with auto-scaling

### Scaling Strategy
- **Horizontal:** Auto-scaling groups for API and worker processes
- **Vertical:** RDS instance scaling for database performance
- **Caching:** Redis for session storage and API response caching
- **CDN:** CloudFront for static asset delivery

---

For detailed technical specifications, see the sharded architecture documents in `docs/architecture/` directory.