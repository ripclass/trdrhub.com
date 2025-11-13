# Supabase Environment Variables for Render

## Required Environment Variables

**IMPORTANT**: Supabase uses **ES256 (ECC P-256)** via JWKS, **NOT HS256**. You do **NOT** need `SUPABASE_JWT_SECRET` or `SUPABASE_SERVICE_ROLE_KEY` for authentication.

### 1. Supabase JWKS URL (REQUIRED)

**Variable**: `SUPABASE_JWKS_URL`

**Format**: `https://{your-project-ref}.supabase.co/auth/v1/.well-known/jwks.json`

**Example**: `https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/.well-known/jwks.json`

**How to find it**:
- Your Supabase project URL + `/auth/v1/.well-known/jwks.json`
- Or check: https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/.well-known/jwks.json

**Note**: This is used to fetch the public key (ES256 ECC key) for token verification.

### 2. Supabase Issuer (REQUIRED - or auto-detected)

**Variable**: `SUPABASE_ISSUER`

**Format**: `https://{your-project-ref}.supabase.co/auth/v1`

**Example**: `https://nnmmhgnriisfsncphipd.supabase.co/auth/v1`

**How to find it**:
- Your Supabase project URL + `/auth/v1`
- Or check your Supabase project settings

**Note**: If not set, the code will **auto-detect from the token issuer** when `SUPABASE_JWKS_URL` is configured.

### 3. Supabase Audience (Optional)

**Variable**: `SUPABASE_AUDIENCE`

**Default**: `authenticated`

**Note**: Usually doesn't need to be changed unless you have custom audience settings.

### 4. Supabase JWT Secret (NOT NEEDED for ES256/JWKS)

**Variable**: `SUPABASE_JWT_SECRET` or `SUPABASE_SERVICE_ROLE_KEY`

**Status**: ❌ **NOT REQUIRED** for Supabase authentication

**Why**: Supabase uses **ES256 (ECC)** via JWKS, not HS256. The JWT secret is only needed for HS256 validation, which Supabase doesn't use.

**When you might need it**: Only if you're using legacy HS256 tokens (not standard for Supabase).

## Minimum Required Configuration

**For Supabase authentication to work, you MUST set:**

```bash
SUPABASE_JWKS_URL=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/.well-known/jwks.json
```

**Issuer is auto-detected** from the token if not set, but recommended to set explicitly:

```bash
SUPABASE_ISSUER=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1
```

## Recommended Configuration

```bash
SUPABASE_JWKS_URL=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_ISSUER=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
```

**You do NOT need**:
- ❌ `SUPABASE_JWT_SECRET` (not used for ES256/JWKS)
- ❌ `SUPABASE_SERVICE_ROLE_KEY` (not needed for token validation)

## How to Set in Render

1. Go to your Render dashboard
2. Select your service (`trdrhub-api`)
3. Go to **Environment** tab
4. Click **Add Environment Variable**
5. Add each variable:
   - Key: `SUPABASE_JWT_SECRET`
   - Value: (paste your JWT secret)
6. Repeat for other variables
7. **Save Changes** - Render will automatically redeploy

## Verification

After setting environment variables:

1. Check Render logs for:
   - `"Successfully decoded Supabase token for user: ..."`
   - `"Created/updated external user: ..."`
   
2. If you see warnings:
   - `"Supabase JWT secret not configured"` → Set `SUPABASE_JWT_SECRET`
   - `"No external providers configured"` → Set `SUPABASE_ISSUER` and `SUPABASE_JWKS_URL`

## Troubleshooting

### Error: "No external providers configured"

**Solution**: Set `SUPABASE_JWKS_URL` and optionally `SUPABASE_ISSUER` in Render environment variables.

### Error: "No external provider could authenticate the token"

**Possible causes**:
1. JWKS URL is incorrect or unreachable
2. Token issuer doesn't match configured issuer
3. Token is expired
4. ES256 key verification failed

**Solution**: 
- Verify JWKS URL is correct and accessible: https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/.well-known/jwks.json
- Check token expiration (Supabase tokens expire after 1 hour by default)
- Verify SUPABASE_ISSUER matches token issuer (or let it auto-detect)
- Check backend logs for detailed error messages

### Error: 500 Internal Server Error

**Check backend logs for**:
- Database constraint errors (run migration: `ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL`)
- Missing environment variables
- Token validation errors

## Security Notes

⚠️ **Never commit JWT secrets to git!**

- Use Render's environment variables
- Keep secrets secure
- Rotate secrets periodically
- Use different secrets for dev/staging/production

