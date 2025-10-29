# TRDR Hub LCopilot

> **Bank-Grade Letter of Credit Validation & Compliance Platform**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/react-18+-blue.svg)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue.svg)](https://www.typescriptlang.org)

## 🎯 Overview

TRDR Hub LCopilot is an AI-powered platform that helps Small and Medium-sized Enterprise (SME) exporters and importers in Bangladesh validate Letters of Credit (LCs) with speed and confidence. The platform eliminates the risk of costly LC errors that cause bank rejections, shipment delays, and demurrage fees by combining OCR, rules-based checks, and AI analysis to instantly flag discrepancies against UCP 600 standards.

### 🚀 Key Features

- **📄 Document Processing**: Multi-format upload (PDF, JPG, PNG) with Google DocumentAI OCR
- **⚖️ UCP600 Compliance**: Deterministic rules engine with 60% UCP600 coverage
- **🔒 Bank-Grade Security**: Immutable audit trails, multi-tenant isolation, encryption at rest/transit
- **🌐 Multi-Language**: English and Bangla interface support
- **📊 Real-time Validation**: Sub-30 second validation with >95% accuracy
- **📋 Compliance Reporting**: Bank-ready PDF reports with discrepancy summaries
- **🏦 Bank Integration**: Framework for SWIFT messaging and bank API connectivity
- **☁️ Cloud-Native**: AWS serverless architecture with disaster recovery

## 🏗️ Architecture

This is a **Turborepo monorepo** containing multiple applications:

```
trdrhub.com/
├── apps/
│   ├── api/          # FastAPI backend (Python)
│   └── web/          # React frontend (TypeScript)
├── trdrhub-suite/    # Additional React application
├── packages/         # Shared packages
└── docs/            # Comprehensive documentation
```

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Backend** | FastAPI | 0.104.1 | High-performance Python API |
| **Frontend** | React + TypeScript | 18+ | Modern web interface |
| **Database** | PostgreSQL | 15+ | Multi-tenant data storage |
| **OCR** | Google DocumentAI | 2.27.0 | Document text extraction |
| **Storage** | Amazon S3 | - | Encrypted file storage |
| **Queue** | Celery + Redis | 5.3.4 | Async task processing |
| **Monitoring** | CloudWatch | - | Observability and alerting |
| **Infrastructure** | AWS CDK | - | Infrastructure as Code |

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm 10+
- **Python** 3.11+
- **PostgreSQL** 15+
- **Redis** (for task queue)
- **AWS CLI** configured (for production)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ripclass/trdrhub.com.git
   cd trdrhub.com
   ```

2. **Install dependencies**
   ```bash
   # Install root dependencies
   npm install
   
   # Install API dependencies
   cd apps/api
   pip install -r requirements.txt
   
   # Install frontend dependencies
   cd ../web
   npm install
   ```

3. **Environment Configuration**
   ```bash
   # Copy environment templates
   cp apps/api/.env.example apps/api/.env
   cp apps/web/.env.example apps/web/.env
   
   # Configure your environment variables
   # See Configuration section below
   ```

4. **Database Setup**
   ```bash
   # Start PostgreSQL and Redis
   # Create database
   createdb lcopilot_dev
   
   # Run migrations
   cd apps/api
   alembic upgrade head
   ```

5. **Start Development Servers**
   ```bash
   # From project root - starts all services
   npm run dev
   
   # Or start individually:
   # Backend: cd apps/api && python main.py
   # Frontend: cd apps/web && npm run dev
   ```

### 🐳 Docker Setup (Alternative)

```bash
# Using Docker Compose
docker-compose up -d

# This starts:
# - PostgreSQL database
# - Redis cache
# - FastAPI backend
# - React frontend
```

## ⚙️ Configuration

### Environment Variables

#### Backend (apps/api/.env)
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/lcopilot_dev

# Google Cloud DocumentAI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_DOCUMENTAI_LOCATION=eu
GOOGLE_DOCUMENTAI_PROCESSOR_ID=your-processor-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# AWS S3
AWS_REGION=eu-north-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=your-bucket-name

# Security
JWT_SECRET_KEY=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key

# Development
USE_STUBS=true  # Use local storage instead of S3
DEBUG=true
```

#### Frontend (apps/web/.env)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=LCopilot
VITE_APP_VERSION=1.0.0
```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Project Brief](docs/brief.md)** - Executive summary and problem statement
- **[Product Requirements](docs/prd.md)** - Detailed feature specifications
- **[Architecture](docs/architecture.md)** - Technical architecture and design
- **[API Documentation](USAGE_EXAMPLE.md)** - API usage examples and endpoints
- **[Compliance Guide](docs/compliance/)** - Regulatory compliance documentation

### Key Documentation Sections

| Document | Description |
|----------|-------------|
| [Executive Summary](docs/brief/executive-summary.md) | High-level project overview |
| [Problem & Users](docs/prd/2-problem-users-jobs.md) | User personas and pain points |
| [Feature Specs](docs/prd/5-feature-specs.md) | Detailed feature specifications |
| [Tech Stack](docs/architecture/tech-stack.md) | Technology choices and rationale |
| [Security Guide](docs/security-scanning.md) | Security implementation details |

## 🎯 Target Users

### Primary: SME Export Managers
- **Profile**: 50-person textile companies in Bangladesh
- **Pain Points**: Manual LC validation, expensive consultants ($200-500), 2-5 day delays
- **Solution**: 30-second validation, <$50 cost, >95% accuracy

### Secondary: Bank Trade Finance Officers
- **Profile**: Commercial bank trade finance departments
- **Pain Points**: Manual review volume, consistency issues, audit documentation
- **Solution**: Automated compliance checking, audit trails, regulatory reporting

### Tertiary: Compliance Officers
- **Profile**: Regional bank compliance teams
- **Pain Points**: Manual audit preparation, regulatory reporting
- **Solution**: Immutable audit trails, automated compliance reports

## 🔧 Development

### Project Structure

```
apps/api/                    # FastAPI Backend
├── app/
│   ├── core/               # Core business logic
│   ├── models/             # Database models
│   ├── routers/            # API endpoints
│   ├── services/           # Business services
│   ├── rules/              # UCP600 validation rules
│   └── middleware/         # Custom middleware
├── alembic/                # Database migrations
├── tests/                  # Test suite
└── main.py                 # Application entry point

apps/web/                   # React Frontend
├── src/
│   ├── components/         # React components
│   ├── pages/              # Page components
│   ├── hooks/              # Custom hooks
│   ├── services/           # API services
│   └── locales/            # i18n translations
├── public/                 # Static assets
└── tests/                  # Test suite
```

### Available Scripts

```bash
# Root level (Turborepo)
npm run dev          # Start all development servers
npm run build        # Build all applications
npm run lint         # Lint all code
npm run test         # Run all tests
npm run type-check   # TypeScript type checking

# Backend (apps/api)
python main.py       # Start FastAPI server
pytest              # Run Python tests
alembic upgrade head # Run database migrations

# Frontend (apps/web)
npm run dev         # Start Vite dev server
npm run build       # Build for production
npm run preview     # Preview production build
```

### Testing

```bash
# Backend tests
cd apps/api
pytest tests/ -v

# Frontend tests
cd apps/web
npm run test

# E2E tests
npm run test:e2e

# All tests
npm run test
```

## 🚀 Deployment

### AWS Deployment

The application is designed for AWS serverless deployment:

```bash
# Deploy infrastructure
cd apps/api/cdk
cdk deploy

# Deploy application
cd apps/api
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Production Environment

- **API**: AWS Lambda + API Gateway
- **Database**: Amazon RDS PostgreSQL
- **Storage**: Amazon S3 with KMS encryption
- **Monitoring**: CloudWatch + X-Ray
- **Secrets**: AWS Secrets Manager

## 🔒 Security

- **Encryption**: AES-256 at rest, TLS 1.3 in transit
- **Authentication**: JWT with OAuth2 refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **Audit**: Immutable hash-chained audit logs
- **Multi-tenancy**: Row-level security (RLS) isolation
- **Compliance**: UCP600, ISBP 745, eUCP 2.1 framework ready

## 📊 Monitoring & Observability

- **Health Checks**: Automated system health monitoring
- **Metrics**: Performance and business metrics
- **Logging**: Structured logging with CloudWatch
- **Alerting**: Multi-channel alert system (Slack, email, PagerDuty)
- **Disaster Recovery**: Automated backup and recovery

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow the existing code style and patterns
- Write tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `docs/` directory
- **Issues**: Open an issue on GitHub
- **Email**: support@trdrhub.com

## 🗺️ Roadmap

### Phase 1: Core Platform (Current)
- ✅ Document processing and OCR
- ✅ UCP600 rules validation
- ✅ Multi-tenant security
- ✅ Audit trail system

### Phase 2: AI Enhancement (Q2 2025)
- 🔄 LLM-assisted validation
- 🔄 Multilingual support (Bangla)
- 🔄 Advanced compliance reporting

### Phase 3: Bank Integration (Q3 2025)
- 📋 SWIFT message processing
- 📋 Bank API connectors
- 📋 eUCP 2.1 support

### Phase 4: Enterprise Features (Q4 2025)
- 📋 Advanced analytics
- 📋 Mobile applications
- 📋 White-label solutions

---

**Built with ❤️ for the global trade finance community**
