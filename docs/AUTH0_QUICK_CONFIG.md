# Auth0 Quick Configuration Reference

## Direct Auth0 Integration (No Supabase Auth Needed)

Since Supabase doesn't have Auth0 as a built-in provider, we're using **direct Auth0 integration**. Users log in directly with Auth0, and the backend validates Auth0 tokens.

## Your Current Values

### Auth0
- **Domain**: `dev-2zhljb8cf2kc2h5t.us.auth0.com`
- **Issuer**: `https://dev-2zhljb8cf2kc2h5t.us.auth0.com/`
- **JWKS URL**: `https://dev-2zhljb8cf2kc2h5t.us.auth0.com/.well-known/jwks.json`
- **Client ID**: ⚠️ **Get from Auth0 Dashboard → Applications → Your App**
- **Audience**: ⚠️ **Get from Auth0 Dashboard → APIs → Your API → Identifier**

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

## Vercel Environment Variables (Frontend)

```bash
# Auth0 Configuration
VITE_AUTH0_DOMAIN=dev-2zhljb8cf2kc2h5t.us.auth0.com
VITE_AUTH0_CLIENT_ID=your-auth0-client-id-here
VITE_AUTH0_AUDIENCE=https://your-api-identifier-here
```

**⚠️ Get these from Auth0 Dashboard:**
- **VITE_AUTH0_CLIENT_ID**: Applications → Your App → Client ID
- **VITE_AUTH0_AUDIENCE**: APIs → Your API → Identifier

## Render Environment Variables (Backend)

```bash
# Auth0 Authentication (for token validation)
AUTH0_ISSUER=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/
AUTH0_AUDIENCE=https://your-api-identifier-here
AUTH0_JWKS_URL=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/.well-known/jwks.json
```

**⚠️ Remember**: Replace `https://your-api-identifier-here` with your actual Auth0 API Identifier!

## Auth0 Dashboard Configuration

### Application Settings
- **Allowed Callback URLs**: 
  ```
  https://trdrhub.com/auth/callback,http://localhost:5173/auth/callback
  ```
- **Allowed Web Origins**: 
  ```
  https://trdrhub.com,http://localhost:5173
  ```
- **Allowed Logout URLs**: 
  ```
  https://trdrhub.com,http://localhost:5173
  ```

**Note**: No Supabase callback URL needed - we're using direct Auth0 integration!

## Testing Checklist

- [ ] Auth0 provider enabled in Supabase
- [ ] Auth0 Application configured with correct callback URLs
- [ ] Auth0 API created and Identifier copied
- [ ] Backend environment variables set in Render
- [ ] Frontend has `loginWithAuth0` button
- [ ] Test login flow end-to-end

