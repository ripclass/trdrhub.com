# Auth0 Quick Configuration Reference

## Supabase Third Party Auth (Simplified!)

Supabase supports Auth0 as a **Third Party Auth** provider. You only need to provide your Auth0 domain - Supabase handles everything else!

## Your Current Values

### Supabase Configuration
- **Auth0 Domain**: `dev-2zhljb8cf2kc2h5t.us` ✅ **Already configured in Supabase Dashboard**
- **Status**: ✅ **Enabled**

### Auth0 (for backend token validation)
- **Domain**: `dev-2zhljb8cf2kc2h5t.us.auth0.com`
- **Issuer**: `https://dev-2zhljb8cf2kc2h5t.us.auth0.com/`
- **JWKS URL**: `https://dev-2zhljb8cf2kc2h5t.us.auth0.com/.well-known/jwks.json`
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

**No Auth0 environment variables needed!** Supabase handles Auth0 OAuth automatically. Just make sure you have:

```bash
VITE_SUPABASE_URL=https://nnmmhgnriisfsncphipd.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

That's it! Supabase Third Party Auth handles the rest.

## Render Environment Variables (Backend)

```bash
# Auth0 Authentication (for token validation)
AUTH0_ISSUER=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/
AUTH0_AUDIENCE=https://your-api-identifier-here
AUTH0_JWKS_URL=https://dev-2zhljb8cf2kc2h5t.us.auth0.com/.well-known/jwks.json
```

**⚠️ Remember**: Replace `https://your-api-identifier-here` with your actual Auth0 API Identifier!

## Auth0 Dashboard Configuration

### Application Settings (Optional)

Supabase automatically configures Auth0 callbacks. If you want to customize:

- **Allowed Callback URLs**: 
  ```
  https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/callback,https://trdrhub.com/auth/callback,http://localhost:5173/auth/callback
  ```

**Note**: Supabase handles the callback URL automatically - this is optional!

## Testing Checklist

- [x] Auth0 provider enabled in Supabase ✅ (Already done!)
- [x] Auth0 Domain configured: `dev-2zhljb8cf2kc2h5t.us` ✅
- [ ] Backend environment variables set in Render (AUTH0_ISSUER, AUTH0_AUDIENCE, AUTH0_JWKS_URL)
- [ ] Frontend has `loginWithAuth0` button
- [ ] Test login flow end-to-end

**That's it!** Supabase Third Party Auth is much simpler - no Client ID/Secret needed!

