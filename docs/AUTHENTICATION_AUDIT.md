# Authentication & Routing Audit Report

**Date**: 2025-01-13  
**Status**: CRITICAL ISSUES FOUND

## Issues Identified

### 1. ❌ CRITICAL: Incorrect Routing Logic in Login.tsx

**Problem**: Login routing relies on `profile.role` instead of `backendRole` from onboarding status.

**Affected Users**:
- `rasel@ric.com` (importer) → Goes to exporter dashboard
- `azam@sabl.com` (bank) → Goes to exporter dashboard

**Root Cause**: 
```typescript
// Line 104-106: WRONG - checks profile.role which may be "exporter" for all SME users
} else if (profile.role === "importer") {
  destination = "/lcopilot/importer-dashboard";
```

**Should be**:
```typescript
// Should check backendRole from onboarding status, not profile.role
} else if (backendRole === "importer") {
  destination = "/lcopilot/importer-dashboard";
```

### 2. ❌ CRITICAL: User State Not Properly Cleared on Logout

**Problem**: Logout doesn't clear all authentication state, causing user profiles to intermingle.

**Symptoms**:
- "Azam Chowdhury" showing in one place, "Md Rasel" in another
- User names persist across different logins

**Root Cause**:
- `logout()` only clears Supabase session and sets `user` to null
- Doesn't clear:
  - `localStorage` tokens (`bank_token`, `trdrhub_api_token`, etc.)
  - Other auth providers' state (`BankAuthProvider`, `ExporterAuthProvider`, etc.)
  - CSRF tokens
  - Onboarding state

**Location**: `apps/web/src/hooks/use-auth.tsx:532-538`

### 3. ❌ CRITICAL: Bank Users Routing to Exporter Dashboard

**Problem**: Bank users (`azam@sabl.com`) are routed to exporter dashboard instead of bank dashboard.

**Root Cause**: 
- Line 82-84 checks `backendRole` correctly for bank users
- BUT if onboarding status fails or times out, fallback logic (line 107-109) checks `profile.role` which may be "exporter"
- Bank users' `profile.role` might be "exporter" if they registered as SME

**Location**: `apps/web/src/pages/Login.tsx:82-109`

### 4. ❌ CRITICAL: Combined User Routing Inconsistency

**Problem**: `monty@mei.com` (SME "both") goes to combined dashboard on first registration, but exporter dashboard on relogin.

**Root Cause**:
- Registration correctly routes to combined dashboard
- On relogin, if onboarding status returns empty or `companySize` is missing, defaults to exporter dashboard
- The retry logic (line 153-186) may not be catching all cases

**Location**: `apps/web/src/pages/Login.tsx:88-103, 153-186`

### 5. ❌ CRITICAL: Enterprise Dashboard Not Working

**Problem**: Medium/Large enterprise users (`sumon@stl.com`, `pavel@pth.com`) getting v1 dashboard, can't see user.

**Root Cause**:
- `EnterpriseDashboard` component exists but may not be properly checking authentication
- Or routing is sending them to wrong dashboard
- Need to verify `EnterpriseDashboard` component exists and works

**Location**: `apps/web/src/pages/EnterpriseDashboard.tsx` (need to check)

### 6. ⚠️ MEDIUM: Multiple Auth Providers Conflict

**Problem**: Multiple auth providers (`BankAuthProvider`, `ExporterAuthProvider`, `ImporterAuthProvider`) may be conflicting.

**Symptoms**:
- User state intermingling
- Different dashboards checking different auth states

**Root Cause**:
- Each dashboard has its own auth provider
- No unified state management
- Logout doesn't clear all providers' state

### 7. ⚠️ MEDIUM: Onboarding Status Timing Issues

**Problem**: Onboarding status may return empty or timeout, causing incorrect routing.

**Root Cause**:
- Backend `/onboarding/status` may be slow or return empty data
- Retry logic exists but may not be sufficient
- No proper error handling for empty onboarding data

## Fixes Required

### Priority 1: Fix Login Routing Logic

1. **Always use `backendRole` from onboarding status**, not `profile.role`
2. **Remove fallback to `profile.role`** for critical routing decisions
3. **Add proper error handling** when onboarding status fails

### Priority 2: Fix Logout Function

1. **Clear all localStorage tokens**:
   - `bank_token`
   - `trdrhub_api_token`
   - Any other auth tokens
2. **Clear all auth providers' state**
3. **Clear CSRF tokens**
4. **Force page reload** to ensure clean state

### Priority 3: Fix Bank User Routing

1. **Ensure bank users always check `backendRole`**, not `profile.role`
2. **Fix `BankAuthProvider`** to properly recognize Supabase-authenticated bank users
3. **Remove fallback to `profile.role`** for bank users

### Priority 4: Fix Combined User Routing

1. **Improve retry logic** for onboarding status
2. **Add better default handling** for missing `companySize`
3. **Ensure consistent routing** between registration and login

### Priority 5: Fix Enterprise Dashboard

1. **Verify `EnterpriseDashboard` component** exists and works
2. **Check authentication** in EnterpriseDashboard
3. **Fix routing** for medium/large enterprise users

## Testing Checklist

- [ ] Importer user routes to importer dashboard
- [ ] Bank user routes to bank dashboard
- [ ] SME "both" user routes to combined dashboard consistently
- [ ] Medium enterprise user routes to enterprise dashboard
- [ ] Large enterprise user routes to enterprise dashboard
- [ ] Logout clears all user state
- [ ] User names don't intermingle between logins
- [ ] No v1 dashboards for enterprise users

