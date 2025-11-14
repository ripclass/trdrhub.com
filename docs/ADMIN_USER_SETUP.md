# Admin User Setup Guide

This guide explains how to create or reset an admin user password for accessing the admin console at `https://trdrhub.com/admin`.

## Current Admin User

There is already an admin user in the database:
- **Email**: `admin@trdrhub.com`
- **Role**: `system_admin`
- **Status**: Has password hash set

## Method 1: Reset Password via Backend API Endpoint (Easiest)

The backend has a `/auth/fix-password` endpoint that doesn't require authentication:

```bash
curl -X POST https://trdrhub-api.onrender.com/auth/fix-password \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@trdrhub.com", "password": "YourNewPassword123"}'
```

**Or using PowerShell (Windows):**

```powershell
$body = @{
    email = "admin@trdrhub.com"
    password = "YourNewPassword123"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://trdrhub-api.onrender.com/auth/fix-password" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

**Or using a browser/Postman:**
- URL: `POST https://trdrhub-api.onrender.com/auth/fix-password`
- Body (JSON): `{"email": "admin@trdrhub.com", "password": "YourNewPassword123"}`

**Note**: This endpoint is temporary and should be removed after all admin passwords are set.

## Method 2: Reset Password via Python Script

Use the provided script to reset the password:

```bash
cd apps/api
python scripts/reset_admin_password.py admin@trdrhub.com YourNewPassword123
```

Or set environment variables:

```bash
ADMIN_EMAIL=admin@trdrhub.com ADMIN_PASSWORD=YourNewPassword123 python scripts/reset_admin_password.py
```

**Requirements:**
- Python 3.11+ with backend dependencies installed
- Database connection configured (via environment variables)

## Method 3: Create/Update Admin User via Supabase SQL

You can directly update the password hash in Supabase:

1. **Generate a password hash** using Python:

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")
hashed = pwd_context.hash("YourNewPassword123")
print(hashed)
```

2. **Update the user in Supabase**:

```sql
-- Update existing admin user password
UPDATE users 
SET hashed_password = '$2b$12$...your_generated_hash_here...'
WHERE email = 'admin@trdrhub.com';

-- Or create a new admin user
INSERT INTO users (id, email, full_name, role, hashed_password, is_active, created_at)
VALUES (
  gen_random_uuid(),
  'admin@trdrhub.com',
  'System Administrator',
  'system_admin',
  '$2b$12$...your_generated_hash_here...',
  true,
  NOW()
)
ON CONFLICT (email) DO UPDATE
SET hashed_password = EXCLUDED.hashed_password,
    role = 'system_admin',
    is_active = true;
```

## Method 4: Create New Admin User via Backend API (Requires Existing Admin)

If you already have one admin user, you can create additional admins via the API:

```bash
curl -X POST https://trdrhub-api.onrender.com/admin/users \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newadmin@trdrhub.com",
    "full_name": "New Admin",
    "password": "SecurePassword123",
    "role": "system_admin"
  }'
```

## Verifying Admin Access

After setting the password:

1. Go to `https://trdrhub.com/admin/login`
2. Enter the admin email and password
3. You should be redirected to the admin dashboard

## Troubleshooting

### "Invalid credentials" error
- Verify the user exists: `SELECT email, role FROM users WHERE email = 'admin@trdrhub.com';`
- Check that `hashed_password` is not NULL
- Ensure the password hash was generated correctly (bcrypt_sha256 format)

### "This account does not have admin permissions" error
- Verify the user role: `SELECT role FROM users WHERE email = 'admin@trdrhub.com';`
- Role must be `system_admin` or `tenant_admin`
- Update if needed: `UPDATE users SET role = 'system_admin' WHERE email = 'admin@trdrhub.com';`

### Password hash format issues
- The backend uses `bcrypt_sha256` scheme from passlib
- If direct SQL updates fail, use Method 1 (Python script) or Method 2 (API endpoint)

## Security Notes

- **Never commit passwords to git**
- **Use strong passwords** (minimum 12 characters, mix of letters, numbers, symbols)
- **Rotate admin passwords regularly**
- **Limit admin user creation** to trusted personnel only
- **Remove `/auth/fix-password` endpoint** after initial setup is complete

