# Database Migration: Make hashed_password Nullable

## Issue

The `users` table has `hashed_password` set as `NOT NULL`, but Supabase users (authenticated via Supabase Auth) don't have backend passwords. This causes database constraint violations when creating Supabase users.

## Solution

Make `hashed_password` nullable in the database to support both:
- **Email/password users**: Have `hashed_password` set
- **Supabase users**: Have `hashed_password = NULL` (password managed by Supabase)

## Migration SQL

Run this migration on your PostgreSQL database:

```sql
-- Make hashed_password nullable
ALTER TABLE users 
ALTER COLUMN hashed_password DROP NOT NULL;

-- Add a check constraint to ensure at least one auth method exists
-- (Either hashed_password OR user must be authenticated via external provider)
-- Note: This is optional, but recommended for data integrity
```

## Verification

After migration, verify:

```sql
-- Check that Supabase users can have NULL password
SELECT id, email, hashed_password, role 
FROM users 
WHERE hashed_password IS NULL;

-- Check that email/password users still have passwords
SELECT id, email, hashed_password IS NOT NULL as has_password, role 
FROM users 
WHERE hashed_password IS NOT NULL;
```

## Code Changes

✅ **Already done**:
- Updated `apps/api/app/models.py` - `hashed_password` is now nullable in model
- Updated `apps/api/app/core/security.py` - `authenticate_user` handles NULL passwords
- Updated `apps/api/app/routers/auth.py` - `/auth/me` has better error handling

## Testing

1. **Email/password registration**: Should create user with `hashed_password` set
2. **Supabase login**: Should work via Supabase token (no backend password needed)
3. **`/auth/me` endpoint**: Should work for both user types

## Rollback

If needed, you can rollback:

```sql
-- Set default password for users without passwords (NOT RECOMMENDED)
UPDATE users 
SET hashed_password = '$2b$12$dummy' 
WHERE hashed_password IS NULL;

-- Make column NOT NULL again
ALTER TABLE users 
ALTER COLUMN hashed_password SET NOT NULL;
```

**Note**: Rollback will break Supabase authentication for existing Supabase users.

