# LCopilot Troubleshooting Guide

## Quick Start Commands

```bash
# 1. Set up database and environment
python setup_db.py

# 2. Test backend API directly
python test_api.py

# 3. Start backend with verbose logging
cd apps/api && python main.py

# 4. Start frontend
cd apps/web && npm run dev
```

## Common Issues

### "Failed to create validation session"

**Symptoms**: Frontend shows session creation error
**Most likely causes**:
1. **Database not initialized** - Run `python setup_db.py`
2. **Backend not running** - Check `http://localhost:8000/health`
3. **Frontend API URL wrong** - Check `VITE_API_URL=http://localhost:8000`

**Debug steps**:
```bash
# Test backend directly
curl http://localhost:8000/health
curl -X POST http://localhost:8000/sessions -H "Content-Type: application/json" -d "{}"

# Check backend logs for errors
cd apps/api && python main.py
```

### Database Connection Errors

**Symptoms**: `psycopg2.OperationalError` or database connection failed
**Solutions**:
```bash
# Install PostgreSQL
brew install postgresql    # Mac
sudo apt-get install postgresql postgresql-contrib    # Ubuntu

# Start PostgreSQL service
brew services start postgresql    # Mac
sudo systemctl start postgresql   # Ubuntu

# Or use Docker
docker run -d --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15
```

### Import/Module Errors

**Symptoms**: `ModuleNotFoundError` or import errors
**Solutions**:
```bash
# Install dependencies
cd apps/api && pip install -r requirements.txt

# Check Python path
cd apps/api && python -c "import app.models; print('✅ Models imported')"
```

### Stub Mode Issues

**Symptoms**: Stub mode not working, scenario files not found
**Solutions**:
```bash
# Enable stub mode
export USE_STUBS=true

# Check stub configuration
curl http://localhost:8000/health/stub-status

# List available scenarios
curl http://localhost:8000/health/stub-scenarios
```

## Environment Configuration

### Required Environment Variables

**For Development (Stub Mode)**:
```bash
USE_STUBS=true
STUB_SCENARIO=lc_happy.json
DATABASE_URL=postgresql://postgres:password@localhost:5432/lcopilot
```

**For Production**:
```bash
USE_STUBS=false
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_DOCUMENTAI_PROCESSOR_ID=your-processor-id
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket
DATABASE_URL=postgresql://user:pass@host:5432/lcopilot
```

### Frontend Environment (.env.local)

```bash
VITE_API_URL=http://localhost:8000
```

## Diagnostic Commands

### Backend Health Check
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy", ...}
```

### Database Check
```bash
# Test database connection
python -c "
from apps.api.app.database import SessionLocal
db = SessionLocal()
db.execute('SELECT 1')
print('✅ Database OK')
"
```

### Frontend API Connection
```bash
# Test from frontend directory
cd apps/web
npm run build    # Check for build errors
```

## Startup Validation

The backend now includes automatic startup validation. Look for these messages:

```
✅ Database connection: OK
✅ Stub scenario file: ./stubs/lc_happy.json
✅ Stub upload directory: /tmp/lcopilot_uploads
✅ All startup validations passed
```

If you see ❌ messages, those indicate configuration issues that need fixing.

## Getting Help

1. **Check startup logs** - The backend prints detailed validation on startup
2. **Run test script** - `python test_api.py` tests all endpoints independently
3. **Check browser network tab** - Look for failed API requests
4. **Verify environment** - Double-check .env files in both apps/api and apps/web

## File Locations

- Backend logs: Terminal output from `python main.py`
- Database setup: `setup_db.py`
- API tests: `test_api.py`  
- Backend config: `apps/api/.env`
- Frontend config: `apps/web/.env.local`
- Stub scenarios: `apps/api/stubs/*.json`