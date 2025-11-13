# Auth0 Quick Configuration Reference

## Required Environment Variables

### Frontend (Vercel)

Add these to your Vercel project settings → Environment Variables:

```bash
VITE_AUTH0_DOMAIN=dev-2zhljb8cf2kc2h5t.us.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id-here
VITE_AUTH0_AUDIENCE=https://your-api-identifier  # Optional
```

**How to get Client ID:**
1. Go to [Auth0 Dashboard](https://manage.auth0.com/)
2. Applications → Your Application → Settings
3. Copy the "Client ID" value

**How to get Audience (if using Auth0 API):**
1. Auth0 Dashboard → APIs → Your API (or create one)
2. Copy the "Identifier" value

### Backend (Render)

Add these to your Render service → Environment Variables:

```bash
AUTH0_ISSUER=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/
AUTH0_AUDIENCE=https://your-api-identifier
AUTH0_JWKS_URL=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/.well-known/jwks.json
```

## Auth0 Application Configuration

In Auth0 Dashboard → Applications → Your Application → Settings:

- **Application Type**: Single Page Application
- **Allowed Callback URLs**: 
  - `https://trdrhub.com/auth/callback`
  - `http://localhost:5173/auth/callback` (for local dev)
- **Allowed Logout URLs**:
  - `https://trdrhub.com`
  - `http://localhost:5173` (for local dev)
- **Allowed Web Origins**:
  - `https://trdrhub.com`
  - `http://localhost:5173` (for local dev)

## Quick Test

1. Set environment variables in Vercel and Render
2. Deploy frontend and backend
3. Go to `https://trdrhub.com/register`
4. Click "Sign up with Auth0"
5. Complete Auth0 signup/login
6. Should redirect to onboarding wizard

## Troubleshooting

**Error: "Unsupported provider: Provider auth0 could not be found"**
- ✅ Fixed: We're now using Auth0 directly, not through Supabase

**Error: "client requires organization membership, but user does not belong to any organization"**
- **Fix**: Disable organization requirement in Auth0 Dashboard
  - Applications → Your App → Settings → Advanced Settings → OAuth
  - Set "Require Organization" to OFF
  - See `docs/AUTH0_ORGANIZATION_FIX.md` for detailed instructions

**Error: "No Auth0 token available"**
- Check `VITE_AUTH0_DOMAIN` and `VITE_AUTH0_CLIENT_ID` are set
- Verify Auth0 application type is "Single Page Application"

**Error: "Redirect URI mismatch"**
- Check callback URLs in Auth0 Dashboard match exactly
- Must include `https://trdrhub.com/auth/callback`
