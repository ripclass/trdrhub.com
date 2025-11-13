# Backend Timeout Debugging Guide

## Current Symptoms

- **CSRF token fetch**: `NetworkError when attempting to fetch resource`
- **User profile**: `Loading profile timed out`
- **Onboarding status**: `Request aborted`

## Root Cause Analysis

These errors suggest the backend is either:
1. **Not running** (crashed on startup)
2. **Timing out** (hanging on JWKS fetch or token validation)
3. **Network issue** (CORS or connectivity)

## Step 1: Check Backend Health

Test if the backend is responding:

```bash
# Check if backend is alive
curl https://trdrhub-api.onrender.com/health/live

# Should return: {"status": "alive"}
```

If this fails → **Backend is down** → Check Render logs for startup errors.

## Step 2: Check Render Logs

1. Go to Render Dashboard → Your Service (`trdrhub-api`)
2. Click **"Logs"** tab
3. Look for:
   - **Startup errors** (syntax errors, import errors)
   - **JWKS fetch errors** (`_get_jwks` failures)
   - **Token validation errors** (`verify_jwt` failures)
   - **Database connection errors**

## Step 3: Verify Environment Variables

In Render Dashboard → Environment Variables, ensure:

```bash
SUPABASE_JWKS_URL=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_ISSUER=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1
```

**Check**: Are these set? If not, add them and redeploy.

## Step 4: Test JWKS Endpoint Directly

Verify JWKS URL is accessible:

```bash
curl https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/.well-known/jwks.json
```

Should return JSON with keys array.

## Step 5: Check Backend Logs for Specific Errors

Look for these log messages in Render:

### Success Messages:
- `"Auto-detected Supabase issuer from token: ..."`
- `"Trying X JWKS provider(s) for ES256/RS256 validation"`
- `"Successfully verified token via provider: supabase"`
- `"Created/updated external user: ..."`

### Error Messages:
- `"No external providers configured"` → Missing env vars
- `"Provider supabase failed: ..."` → JWKS fetch or validation error
- `"No matching signing key"` → Key ID mismatch
- `"Unknown token issuer"` → Issuer mismatch

## Step 6: Common Issues & Fixes

### Issue: "No external providers configured"

**Fix**: Set `SUPABASE_JWKS_URL` and optionally `SUPABASE_ISSUER` in Render.

### Issue: "Provider supabase failed: No matching signing key"

**Fix**: 
- Verify JWKS URL is correct
- Check if key ID (`kid`) in token matches JWKS
- Token might be expired - try logging in again

### Issue: "Provider supabase failed: Unknown token issuer"

**Fix**: 
- Set `SUPABASE_ISSUER` explicitly (or let it auto-detect)
- Ensure issuer matches token issuer exactly (no trailing slash)

### Issue: Backend crashes on startup

**Check Render logs for**:
- Python syntax errors
- Import errors (`ModuleNotFoundError`)
- Database connection failures
- Missing environment variables

## Step 7: Test Token Validation Manually

If backend is running, test token validation:

```bash
# Get a Supabase token (from browser localStorage or Supabase dashboard)
TOKEN="your-supabase-token-here"

# Test /auth/me endpoint
curl -H "Authorization: Bearer $TOKEN" \
     https://trdrhub-api.onrender.com/auth/me
```

Expected:
- **200 OK** with user profile → Working!
- **401 Unauthorized** → Token invalid/expired
- **500 Internal Server Error** → Check backend logs
- **Timeout** → Backend is hanging (check JWKS fetch)

## Step 8: Check Network Tab in Browser

1. Open browser DevTools → Network tab
2. Try to log in
3. Check requests:
   - `/auth/csrf-token` → Should return 200
   - `/auth/me` → Check status code and response

## Quick Fix Checklist

- [ ] Backend is deployed and running (check `/health/live`)
- [ ] `SUPABASE_JWKS_URL` is set in Render
- [ ] `SUPABASE_ISSUER` is set (or auto-detected)
- [ ] JWKS URL is accessible (test with curl)
- [ ] No startup errors in Render logs
- [ ] Token validation errors logged in Render logs
- [ ] CORS is configured correctly

## Next Steps

1. **Check Render logs first** → This will tell you exactly what's failing
2. **Verify environment variables** → Most common issue
3. **Test health endpoint** → Confirm backend is running
4. **Check JWKS accessibility** → Ensure Supabase endpoint is reachable

