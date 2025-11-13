# Auth0 Setup Guide - Direct Integration

This guide explains how to configure Auth0 for direct integration (bypassing Supabase OAuth).

## Overview

**Direct Auth0 Integration**: We use Auth0 directly via `@auth0/auth0-spa-js` SDK. Auth0 handles authentication, and our backend validates Auth0 tokens. This gives us full control over the Auth0 flow.

## Step 1: Configure Auth0 Application

1. **Go to Auth0 Dashboard** → Applications → Your Application (or create a new one)
2. **Settings tab:**
   - **Application Type**: Single Page Application
   - **Allowed Callback URLs**: Add:
     - `https://trdrhub.com/auth/callback`
     - `http://localhost:5173/auth/callback` (development)
   - **Allowed Logout URLs**: Add:
     - `https://trdrhub.com`
     - `http://localhost:5173` (development)
   - **Allowed Web Origins**: Add:
     - `https://trdrhub.com`
     - `http://localhost:5173` (development)

3. **Copy these values:**
   - **Domain**: `dev-2zhljb8cf2kc2h5t.us.auth0.com` (or your Auth0 domain)
   - **Client ID**: Copy from the Settings tab

## Step 2: Configure Frontend Environment Variables

Add these to your frontend `.env` file (or Vercel environment variables):

```bash
VITE_AUTH0_DOMAIN=dev-2zhljb8cf2kc2h5t.us.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id-here
VITE_AUTH0_AUDIENCE=https://your-api-identifier  # Optional: API identifier if using Auth0 API
```

**Important**: 
- `VITE_AUTH0_DOMAIN`: Your Auth0 domain (e.g., `dev-2zhljb8cf2kc2h5t.us.auth0.com`)
- `VITE_AUTH0_CLIENT_ID`: Copy from Auth0 Dashboard → Applications → Your App → Settings
- `VITE_AUTH0_AUDIENCE`: Optional - Only needed if you're using Auth0 API. Get from Auth0 Dashboard → APIs → Your API → Identifier

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

**Important**: These are REQUIRED for direct Auth0 integration. The backend validates Auth0 tokens directly.

## Step 4: Frontend is Ready!

The frontend already supports Auth0 login. The registration page has a "Sign up with Auth0" button that triggers the Auth0 flow.

## Step 5: Test the Flow

1. **Click "Sign up with Auth0"** on the registration page (`/register`)
2. **Auth0 redirects to login/signup** page
3. **After login/signup**, Auth0 redirects back to `/auth/callback`
4. **Frontend gets Auth0 token** and sends it to backend
5. **Backend validates Auth0 token** and creates/updates user
6. **Backend returns JWT token** for API calls
7. **User is redirected** to onboarding wizard (if incomplete) or dashboard

## Troubleshooting

### Issue: "Unsupported provider: Provider auth0 could not be found"
- **Solution**: This error occurs if you try to use Supabase's OAuth. We're using Auth0 directly, so this shouldn't happen. Make sure you're using `loginWithAuth0()` from `use-auth` hook, not Supabase's `signInWithOAuth`.

### Issue: "Redirect URI mismatch"
- **Solution**: Check that callback URLs in Auth0 Dashboard match exactly:
  - Production: `https://trdrhub.com/auth/callback`
  - Development: `http://localhost:5173/auth/callback`

### Issue: "Backend authentication fails"
- **Solution**: 
  - Ensure backend has Auth0 environment variables configured (`AUTH0_ISSUER`, `AUTH0_AUDIENCE`, `AUTH0_JWKS_URL`)
  - Check that Auth0 API is created and identifier matches `AUTH0_AUDIENCE`
  - Verify backend `/auth/auth0` endpoint is working

### Issue: "No Auth0 token available"
- **Solution**: 
  - Check that `VITE_AUTH0_DOMAIN` and `VITE_AUTH0_CLIENT_ID` are set in frontend environment variables
  - Verify Auth0 application is configured as "Single Page Application"
  - Check browser console for Auth0 SDK errors

### Issue: "User not created in backend"
- **Solution**: Backend automatically creates users from Auth0 tokens. Check backend logs for errors. Ensure backend `/auth/auth0` endpoint is properly configured.

## Environment Variables Summary

### Frontend (Vercel)
```bash
# Auth0 Configuration (REQUIRED)
VITE_AUTH0_DOMAIN=dev-2zhljb8cf2kc2h5t.us.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id-from-auth0-dashboard
VITE_AUTH0_AUDIENCE=https://your-api-identifier  # Optional: Only if using Auth0 API

# API Configuration
VITE_API_URL=https://trdrhub-api.onrender.com
```

### Backend (Render)
```bash
# Auth0 Configuration (REQUIRED for token validation)
AUTH0_ISSUER=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/
AUTH0_AUDIENCE=https://your-api-identifier  # Get this from Auth0 Dashboard → APIs → Your API → Identifier
AUTH0_JWKS_URL=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/.well-known/jwks.json

# Database (Supabase - still needed)
DATABASE_URL=your-postgres-connection-string
```

**Quick Reference - Your Values:**
- Auth0 Domain: `dev-2zhljb8cf2kc2h5t.us.auth0.com`
- Auth0 Client ID: **Get from Auth0 Dashboard → Applications → Your App → Settings**
- Auth0 Audience: **Get from Auth0 Dashboard → APIs → Your API → Identifier** (create API if needed)

## Next Steps

1. Test login flow end-to-end
2. Verify user creation in backend database
3. Test admin endpoints with Auth0-authenticated users
4. Configure user roles in Auth0 (if needed)

