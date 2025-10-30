# Backend Setup Guide

## Prerequisites

### 1. Install PostgreSQL
**Windows:**
```bash
# Download from https://www.postgresql.org/download/windows/
# Or use Chocolatey:
choco install postgresql

# Or use Scoop:
scoop install postgresql
```

**macOS:**
```bash
# Using Homebrew:
brew install postgresql
brew services start postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Install Redis (Optional but recommended)
**Windows:**
```bash
# Download from https://github.com/microsoftarchive/redis/releases
# Or use Chocolatey:
choco install redis-64
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux:**
```bash
sudo apt install redis-server
sudo systemctl start redis-server
```

## Database Setup

### 1. Create Database
```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database and user
CREATE DATABASE lcopilot;
CREATE USER lcopilot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE lcopilot TO lcopilot_user;
\q
```

### 2. Environment Configuration
Create `.env` file in `apps/api/`:
```env
# Database
DATABASE_URL=postgresql://lcopilot_user:your_secure_password@localhost:5432/lcopilot

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Application
ENVIRONMENT=development
DEBUG=true
USE_STUBS=true

# Security
SECRET_KEY=your-super-secret-key-change-in-production

# AWS (for production)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=your-bucket-name

# Google Cloud (for OCR)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_DOCUMENTAI_PROCESSOR_ID=your-processor-id
```

## Backend Setup

### 1. Install Dependencies
```bash
cd apps/api
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run Database Migrations
```bash
cd apps/api
alembic upgrade head
```

### 3. Start the Backend
```bash
# Development mode
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the Makefile
make dev
```

## Verification

### 1. Check API Health
```bash
curl http://localhost:8000/health
```

### 2. Check API Documentation
Open: http://localhost:8000/docs

### 3. Test Database Connection
```bash
curl http://localhost:8000/debug/db-status
```

## Production Deployment Options

### Option A: Railway (Recommended)
1. Connect your GitHub repo to Railway
2. Add environment variables
3. Deploy automatically

### Option B: Render
1. Create new Web Service
2. Connect GitHub repo
3. Set build command: `cd apps/api && pip install -r requirements.txt`
4. Set start command: `cd apps/api && uvicorn main:app --host 0.0.0.0 --port $PORT`

### Option C: AWS ECS/Fargate
1. Create ECS cluster
2. Use the provided Dockerfile
3. Set up RDS for PostgreSQL
4. Configure load balancer

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check PostgreSQL is running
   - Verify DATABASE_URL format
   - Ensure user has proper permissions

2. **Port Already in Use**
   - Change port in uvicorn command
   - Kill existing process: `lsof -ti:8000 | xargs kill`

3. **Migration Errors**
   - Check alembic.ini configuration
   - Ensure DATABASE_URL is correct
   - Run: `alembic current` to check status

4. **Import Errors**
   - Activate virtual environment
   - Install all requirements
   - Check Python path
