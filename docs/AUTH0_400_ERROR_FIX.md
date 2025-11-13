# Fix Auth0 400 Error on Signup

## Error

```
POST https://dev-2zhljb8cf2kc2h5t.us.auth0.com/u/signup?state=...
[HTTP/3 400]
```

## Common Causes

### 1. Callback URL Mismatch

**Most Common Issue**: The callback URL in your code doesn't match what's configured in Auth0 Dashboard.

**Fix:**
1. Go to Auth0 Dashboard → Applications → Your Application → Settings
2. Check "Allowed Callback URLs"
3. Must include **exactly**:
   - `https://trdrhub.com/auth/callback` (production)
   - `http://localhost:5173/auth/callback` (development)
4. URLs are case-sensitive and must match exactly (including protocol and trailing slashes)

### 2. Missing Required Scopes

**Fix:**
- Ensure your Auth0 application has these scopes enabled:
  - `openid` (required)
  - `profile` (for user profile info)
  - `email` (for email address)

### 3. Application Type Mismatch

**Fix:**
1. Auth0 Dashboard → Applications → Your Application → Settings
2. **Application Type** must be: **Single Page Application**
3. If it's set to "Regular Web Application" or "Native", change it to "Single Page Application"

### 4. Organization Requirement Still Enabled

**Fix:**
1. Auth0 Dashboard → Applications → Your Application → Settings
2. **Advanced Settings** → **OAuth** tab
3. **Organization Usage** → Set "Require Organization" to **OFF**
4. Save changes

### 5. Invalid Client ID or Domain

**Fix:**
1. Verify environment variables are set correctly:
   ```bash
   VITE_AUTH0_DOMAIN=dev-2zhljb8cf2kc2h5t.us.auth0.com
   VITE_AUTH0_CLIENT_ID=your-actual-client-id
   ```
2. Check Auth0 Dashboard → Applications → Your Application → Settings
3. Copy the exact **Domain** and **Client ID** values

### 6. CORS Issues

**Fix:**
1. Auth0 Dashboard → Applications → Your Application → Settings
2. **Allowed Web Origins** must include:
   - `https://trdrhub.com`
   - `http://localhost:5173` (development)
3. **Allowed Logout URLs** must include:
   - `https://trdrhub.com`
   - `http://localhost:5173` (development)

## Step-by-Step Verification Checklist

- [ ] **Callback URLs** match exactly in Auth0 Dashboard
- [ ] **Application Type** is "Single Page Application"
- [ ] **Organization Requirement** is disabled
- [ ] **Environment variables** are set correctly (`VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`)
- [ ] **Allowed Web Origins** includes your domain
- [ ] **Allowed Logout URLs** includes your domain
- [ ] **Client ID** matches exactly (no extra spaces or characters)

## Debug Steps

1. **Check Browser Console** for detailed error messages
2. **Check Auth0 Logs**: Dashboard → Monitoring → Logs
   - Look for errors around the time of the 400 request
   - Check the error description for specific issues
3. **Verify Network Request**:
   - Open browser DevTools → Network tab
   - Look at the failed request to `/u/signup`
   - Check the request URL parameters
   - Check response body for error details

## Quick Test

After making changes:

1. **Clear browser cache and localStorage**
2. **Open incognito/private window**
3. **Go to** `https://trdrhub.com/register`
4. **Click "Sign up with Auth0"**
5. **Check if signup page loads** (should not show 400 error)

## Still Getting 400?

If the error persists:

1. **Check Auth0 Logs** for detailed error message
2. **Verify all URLs** match exactly (no trailing slashes, correct protocol)
3. **Try creating a new Auth0 Application** with fresh configuration
4. **Contact Auth0 Support** with the error details from logs

## Common Error Messages in Auth0 Logs

- **"invalid_request"**: Usually means callback URL mismatch or missing required parameter
- **"unauthorized_client"**: Client ID doesn't match or application type is wrong
- **"access_denied"**: Organization requirement or other access restriction
- **"invalid_scope"**: Missing required scopes

