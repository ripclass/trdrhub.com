# Supabase Environment Variables for Render

## Required Environment Variables

For Supabase authentication to work, you need to set these environment variables in your Render dashboard:

### 1. Supabase JWT Secret (CRITICAL)

**Variable**: `SUPABASE_JWT_SECRET`

**How to find it**:
1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **API**
3. Look for **JWT Secret** (under "Project API keys")
4. Copy the JWT Secret value

**OR** use your Service Role Key (they're often the same):
- **Variable**: `SUPABASE_SERVICE_ROLE_KEY`
- Found in the same Settings → API page

**Note**: The code will try `SUPABASE_JWT_SECRET` first, then fall back to `SUPABASE_SERVICE_ROLE_KEY` if JWT secret is not set.

### 2. Supabase Issuer (Optional but Recommended)

**Variable**: `SUPABASE_ISSUER`

**Format**: `https://{your-project-ref}.supabase.co/auth/v1`

**Example**: `https://nnmmhgnriisfsncphipd.supabase.co/auth/v1`

**How to find it**:
- Your Supabase project URL + `/auth/v1`
- Or check your Supabase project settings

**Note**: If not set, the code will auto-detect from the token issuer.

### 3. Supabase Audience (Optional)

**Variable**: `SUPABASE_AUDIENCE`

**Default**: `authenticated`

**Note**: Usually doesn't need to be changed unless you have custom audience settings.

### 4. Supabase JWKS URL (Optional - for JWKS validation fallback)

**Variable**: `SUPABASE_JWKS_URL`

**Format**: `https://{your-project-ref}.supabase.co/auth/v1/.well-known/jwks.json`

**Example**: `https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/.well-known/jwks.json`

**Note**: Only needed if HS256 validation fails. The code prefers HS256 (simpler, faster).

## Minimum Required Configuration

**For basic Supabase authentication to work, you MUST set:**

```bash
SUPABASE_JWT_SECRET=your-jwt-secret-here
```

**OR**

```bash
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

## Recommended Configuration

```bash
SUPABASE_JWT_SECRET=your-jwt-secret-here
SUPABASE_ISSUER=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
```

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

### Error: "Supabase JWT secret not configured"

**Solution**: Set `SUPABASE_JWT_SECRET` or `SUPABASE_SERVICE_ROLE_KEY` in Render environment variables.

### Error: "No external provider could authenticate the token"

**Possible causes**:
1. JWT secret is incorrect
2. Token issuer doesn't match configured issuer
3. Token is expired

**Solution**: 
- Verify JWT secret matches your Supabase project
- Check token expiration (Supabase tokens expire after 1 hour by default)
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

