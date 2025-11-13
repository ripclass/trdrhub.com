# Auth0 Setup Guide - Direct Integration

This guide explains how to configure Auth0 as a direct authentication provider (bypassing Supabase auth).

## Overview

**Direct Auth0 Integration**: Users log in directly with Auth0, and the backend validates Auth0 tokens. This is simpler and more reliable than trying to use Supabase as a proxy (since Supabase doesn't have Auth0 as a built-in provider).

## Step 1: Configure Auth0 Application

1. **Go to Auth0 Dashboard** → Applications → Your Application
2. **Settings tab:**
   - **Allowed Callback URLs**: Add:
     - `https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/callback`
     - `https://trdrhub.com/auth/callback`
     - `http://localhost:5173/auth/callback`
   - **Allowed Web Origins**: Add:
     - `https://trdrhub.com`
     - `http://localhost:5173`
   - **Allowed Logout URLs**: Add:
     - `https://trdrhub.com`
     - `http://localhost:5173`

## Step 2: Configure Frontend Environment Variables

Add these to your frontend `.env` file (or Vercel environment variables):

```bash
# Auth0 Configuration
VITE_AUTH0_DOMAIN=dev-2zhljb8cf2kc2h5t.us.auth0.com
VITE_AUTH0_CLIENT_ID=your-auth0-client-id
VITE_AUTH0_AUDIENCE=https://your-api-identifier
```

**Where to get these:**
- **VITE_AUTH0_DOMAIN**: Your Auth0 domain (`dev-2zhljb8cf2kc2h5t.us.auth0.com`)
- **VITE_AUTH0_CLIENT_ID**: Auth0 Dashboard → Applications → Your App → Client ID
- **VITE_AUTH0_AUDIENCE**: Auth0 Dashboard → APIs → Your API → Identifier

## Step 3: Configure Backend Environment Variables

Add these to your backend `.env` file (or Render environment variables):

```bash
# Auth0 Configuration (for direct Auth0 token validation)
AUTH0_ISSUER=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/
AUTH0_AUDIENCE=https://your-api-identifier
AUTH0_JWKS_URL=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/.well-known/jwks.json
```

**Important**: 
- `AUTH0_ISSUER` and `AUTH0_JWKS_URL` are set above with your actual Auth0 domain
- `AUTH0_AUDIENCE` needs to be your Auth0 API Identifier:
  - Go to Auth0 Dashboard → APIs → Your API (or create one)
  - Copy the "Identifier" value (e.g., `https://api.trdrhub.com` or `https://trdrhub-api`)
  - If you don't have an API, create one: APIs → Create API → Set Identifier

**Note**: These are optional if you're using Auth0 via Supabase. The backend will validate Supabase tokens, which contain Auth0 user info. However, it's recommended to set them for direct Auth0 token validation support.

## Step 4: Update Frontend Login

The frontend now supports Auth0 login. Update your login page to include an Auth0 button:

```tsx
import { useAuth } from '@/hooks/use-auth'

function LoginPage() {
  const { loginWithAuth0 } = useAuth()
  
  return (
    <button onClick={loginWithAuth0}>
      Login with Auth0
    </button>
  )
}
```

## Step 5: Test the Flow

1. **Click "Login with Auth0"** on your login page
2. **Redirected to Auth0** login page
3. **After login**, redirected back to Supabase callback
4. **Supabase creates/updates user** with Auth0 user info
5. **Frontend receives Supabase session** token
6. **Backend validates Supabase token** (which contains Auth0 user info)

## Troubleshooting

### Issue: "Provider not enabled"
- **Solution**: Make sure Auth0 is enabled in Supabase Dashboard → Authentication → Providers

### Issue: "Redirect URI mismatch"
- **Solution**: Check that callback URLs in Auth0 match exactly what's configured in Supabase

### Issue: "Backend authentication fails"
- **Solution**: Ensure backend has Auth0 environment variables configured (even if using via Supabase, backend needs them for token validation)

### Issue: "User not created in backend"
- **Solution**: Backend automatically creates users from Auth0 tokens. Check backend logs for errors.

## Alternative: Direct Auth0 (Without Supabase)

If you want to bypass Supabase entirely:

1. **Remove Supabase auth** from frontend
2. **Use Auth0 SDK directly** (`@auth0/auth0-react`)
3. **Configure backend** with Auth0 environment variables
4. **Backend validates Auth0 tokens** directly

This requires more code changes but gives you full control over Auth0.

## Environment Variables Summary

### Frontend (Vercel)
```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### Backend (Render)
```bash
# Supabase (still needed for database)
SUPABASE_ISSUER=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
SUPABASE_JWKS_URL=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/.well-known/jwks.json

# Auth0 (for direct token validation)
AUTH0_ISSUER=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/
AUTH0_AUDIENCE=https://your-api-identifier  # Get this from Auth0 Dashboard → APIs → Your API → Identifier
AUTH0_JWKS_URL=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/.well-known/jwks.json
```

**Quick Reference - Your Values:**
- Supabase Project: `nnmmhgnriisfsncphipd`
- Auth0 Domain: `dev-2zhljb8cf2kc2h5t.us.auth0.com`
- Auth0 Audience: **You need to get this from Auth0 Dashboard → APIs**

## Next Steps

1. Test login flow end-to-end
2. Verify user creation in backend database
3. Test admin endpoints with Auth0-authenticated users
4. Configure user roles in Auth0 (if needed)

