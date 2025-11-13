# Auth0 Quick Configuration Reference

## Your Current Values

### Supabase
- **Project URL**: `https://nnmmhgnriisfsncphipd.supabase.co`
- **Auth Endpoint**: `https://nnmmhgnriisfsncphipd.supabase.co/auth/v1`
- **Callback URL**: `https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/callback`

### Auth0
- **Domain**: `dev-2zhljb8cf2kc2h5t.us.auth0.com`
- **Issuer**: `https://dev-2zhljb8cf2kc2h5t.us.auth0.com/`
- **JWKS URL**: `https://dev-2zhljb8cf2kc2h5t.us.auth0.com/.well-known/jwks.json`
- **Audience**: ⚠️ **You need to get this from Auth0 Dashboard**

## How to Get AUTH0_AUDIENCE

1. **Go to Auth0 Dashboard**: https://manage.auth0.com/
2. **Navigate to**: APIs → APIs (left sidebar)
3. **Either**:
   - **If you have an API**: Click on it → Copy the "Identifier" value
   - **If you don't have an API**: 
     - Click "Create API"
     - Name: `trdrhub-api` (or any name)
     - Identifier: `https://api.trdrhub.com` (or `https://trdrhub-api`)
     - Signing Algorithm: `RS256`
     - Click "Create"
     - Copy the "Identifier" value

**Example Audience values:**
- `https://api.trdrhub.com`
- `https://trdrhub-api`
- `https://trdrhub.com/api`

## Render Environment Variables (Copy-Paste Ready)

```bash
# Supabase Authentication
SUPABASE_ISSUER=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
SUPABASE_JWKS_URL=https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/.well-known/jwks.json

# Auth0 Authentication
AUTH0_ISSUER=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/
AUTH0_AUDIENCE=https://api.trdrhub.com
AUTH0_JWKS_URL=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/.well-known/jwks.json
```

**⚠️ Remember**: Replace `https://api.trdrhub.com` in `AUTH0_AUDIENCE` with your actual Auth0 API Identifier!

## Supabase Dashboard Configuration

### Auth0 Provider Settings
- **Enabled**: ✅ Yes
- **Client ID**: (from Auth0 Dashboard → Applications → Your App)
- **Client Secret**: (from Auth0 Dashboard → Applications → Your App)
- **Domain**: `dev-2zhljb8cf2kc2h5t.us.auth0.com`
- **Redirect URL**: `https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/callback`

## Auth0 Dashboard Configuration

### Application Settings
- **Allowed Callback URLs**: 
  ```
  https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/callback,https://trdrhub.com/auth/callback,http://localhost:5173/auth/callback
  ```
- **Allowed Web Origins**: 
  ```
  https://trdrhub.com,http://localhost:5173
  ```
- **Allowed Logout URLs**: 
  ```
  https://trdrhub.com,http://localhost:5173
  ```

## Testing Checklist

- [ ] Auth0 provider enabled in Supabase
- [ ] Auth0 Application configured with correct callback URLs
- [ ] Auth0 API created and Identifier copied
- [ ] Backend environment variables set in Render
- [ ] Frontend has `loginWithAuth0` button
- [ ] Test login flow end-to-end

