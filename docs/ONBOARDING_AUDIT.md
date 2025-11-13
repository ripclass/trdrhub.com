# User Onboarding Flow Audit

**Date**: 2025-01-12  
**Auditor**: AI Assistant  
**Scope**: Complete user onboarding flow from registration to first successful use

---

## Executive Summary

The onboarding flow has **good foundational structure** but contains **several critical gaps** that can lead to poor user experience, data inconsistency, and security concerns. The system supports multiple registration paths (email/password, Google OAuth, Auth0) but lacks proper coordination between them.

### Overall Assessment: ⚠️ **NEEDS IMPROVEMENT**

**Critical Issues**: 5  
**High Priority**: 8  
**Medium Priority**: 6  
**Low Priority**: 3

---

## 1. Registration Flow Analysis

### 1.1 Email/Password Registration (`/register`)

**Current Flow:**
1. User fills registration form (company name, contact person, email, password, company type)
2. Frontend validates password match and terms agreement
3. Calls `registerWithEmail()` which:
   - Creates user in Supabase Auth
   - Attempts to auto-sign-in if email confirmation is disabled
   - Calls backend `/auth/me` to get user profile
4. Updates onboarding progress (role, company, business types)
5. Redirects to dashboard based on role

**Issues Identified:**

#### 🔴 **CRITICAL: Dual User Creation**
- **Problem**: User is created in **both Supabase Auth AND backend database** separately
- **Location**: `apps/web/src/hooks/use-auth.tsx:212-251` and `apps/api/app/routers/auth.py:26-71`
- **Impact**: 
  - Supabase user exists but backend user may not exist (if `/auth/me` fails)
  - Backend user exists but Supabase session may be invalid
  - Two sources of truth for user data
- **Recommendation**: 
  - Option A: Use Supabase Auth only, backend creates user on first `/auth/me` call
  - Option B: Use backend registration only, Supabase Auth is optional
  - Option C: Ensure backend user creation happens synchronously during registration

#### 🔴 **CRITICAL: Missing Backend User Creation**
- **Problem**: `registerWithEmail()` only creates Supabase user, backend user is created lazily via `/auth/me`
- **Location**: `apps/web/src/hooks/use-auth.tsx:246`
- **Impact**: If `/auth/me` fails, user exists in Supabase but not in backend database
- **Recommendation**: Create backend user explicitly during registration or ensure `/auth/me` creates user if missing

#### 🟠 **HIGH: Email Verification Not Handled**
- **Problem**: Registration mentions "verification email through Supabase Auth" but flow doesn't handle email confirmation requirement
- **Location**: `apps/web/src/pages/Register.tsx:351` and `apps/web/src/hooks/use-auth.tsx:233-242`
- **Impact**: 
  - If email confirmation is enabled in Supabase, user can't log in until verified
  - No UI to show "check your email" state
  - User may be confused why login fails
- **Recommendation**: 
  - Check Supabase email confirmation setting
  - Show appropriate UI based on confirmation requirement
  - Add email verification status check

#### 🟠 **HIGH: Onboarding Progress Update Failure Silent**
- **Problem**: If `updateProgress()` fails, registration still succeeds but onboarding data is incomplete
- **Location**: `apps/web/src/pages/Register.tsx:100-119`
- **Impact**: User is redirected to dashboard but onboarding wizard may not show correct state
- **Recommendation**: 
  - Make onboarding progress update critical (fail registration if it fails)
  - OR: Show warning toast and allow user to complete onboarding later
  - Add retry mechanism

#### 🟡 **MEDIUM: Role Mapping Inconsistency**
- **Problem**: Frontend maps `"both"` → `"exporter"` but stores `['exporter', 'importer']` in business_types
- **Location**: `apps/web/src/pages/Register.tsx:84-91`
- **Impact**: User's role is exporter but they selected "both exporter & importer"
- **Recommendation**: 
  - Create a `tenant_admin` role for users who are both
  - OR: Allow users to have multiple roles
  - OR: Clarify that "both" means they can switch roles later

#### 🟡 **MEDIUM: Password Validation Weak**
- **Problem**: Only checks password match, no strength validation
- **Location**: `apps/web/src/pages/Register.tsx:63-71`
- **Impact**: Weak passwords can be used
- **Recommendation**: Add password strength meter and validation

### 1.2 OAuth Registration (Google/Auth0)

**Current Flow:**
1. User clicks "Sign in with Google/Auth0"
2. Redirected to OAuth provider
3. After authentication, redirected to `/auth/callback`
4. Supabase handles OAuth callback
5. Frontend gets Supabase session
6. Calls backend `/auth/auth0` with Supabase token
7. Backend validates token and creates/updates user via `authenticate_external_token()`
8. Redirects to dashboard

**Issues Identified:**

#### 🔴 **CRITICAL: OAuth Users May Not Have Backend User**
- **Problem**: If backend `/auth/auth0` call fails, user has Supabase session but no backend user
- **Location**: `apps/web/src/pages/auth/Callback.tsx:42-63`
- **Impact**: User can't access backend APIs, dashboard may fail
- **Recommendation**: 
  - Make backend login critical (show error if it fails)
  - OR: Ensure backend user creation happens on first API call
  - Add retry mechanism

#### 🟠 **HIGH: Default Role for OAuth Users**
- **Problem**: OAuth users default to `exporter` role regardless of their actual needs
- **Location**: `apps/api/app/core/security.py:82-97`
- **Impact**: Bank officers logging in with Google will be exporters
- **Recommendation**: 
  - Allow role selection after OAuth login
  - OR: Extract role from OAuth provider claims
  - OR: Show onboarding wizard immediately after OAuth login

#### 🟠 **HIGH: No Onboarding Trigger for OAuth Users**
- **Problem**: OAuth users skip registration form, so onboarding progress is never initialized
- **Location**: `apps/web/src/pages/auth/Callback.tsx:65-70`
- **Impact**: OAuth users may not see onboarding wizard
- **Recommendation**: 
  - Check onboarding status after OAuth login
  - Show onboarding wizard if `needsOnboarding` is true
  - Initialize onboarding progress with default values

#### 🟡 **MEDIUM: User Metadata Not Preserved**
- **Problem**: OAuth user's name/email may not match backend user if user already exists
- **Location**: `apps/api/app/core/security.py:100-132`
- **Impact**: User's display name may be incorrect
- **Recommendation**: Prefer OAuth provider data over existing backend data

---

## 2. Email Verification Flow

### 2.1 Current State

**Status**: ⚠️ **NOT IMPLEMENTED**

- Registration mentions email verification but doesn't handle it
- No UI for "check your email" state
- No email verification status check
- No resend verification email functionality

### 2.2 Recommendations

#### 🔴 **CRITICAL: Implement Email Verification Flow**
1. **Check Supabase email confirmation setting**
   - If enabled: Show "check your email" screen after registration
   - If disabled: Continue with current flow

2. **Add Email Verification Status Check**
   - Check `user.email_confirmed_at` in Supabase session
   - Show verification banner if email not confirmed
   - Block certain actions until email verified

3. **Add Resend Verification Email**
   - Button to resend verification email
   - Rate limiting (max 3 resends per hour)
   - Success/error feedback

4. **Handle Verification Callback**
   - Route: `/auth/verify-email`
   - Verify token and update user status
   - Redirect to dashboard with success message

---

## 3. Onboarding Wizard Flow

### 3.1 Current Implementation

**Location**: `apps/web/src/components/onboarding/OnboardingWizard.tsx`

**Flow:**
1. Wizard opens automatically if `needsOnboarding` is true
2. Steps: role → company → business → review → complete
3. Bank users require KYC approval (status: `under_review`)
4. Non-bank users complete immediately

**Issues Identified:**

#### 🟠 **HIGH: Wizard May Not Show for OAuth Users**
- **Problem**: OAuth users skip registration, onboarding status may not be initialized
- **Location**: `apps/web/src/components/onboarding/OnboardingProvider.tsx:105-108`
- **Impact**: OAuth users may never see onboarding wizard
- **Recommendation**: Initialize onboarding status for OAuth users

#### 🟠 **HIGH: Wizard Can Be Dismissed Without Completion**
- **Problem**: User can close wizard without completing onboarding
- **Location**: `apps/web/src/components/onboarding/OnboardingWizard.tsx:39`
- **Impact**: Incomplete onboarding data
- **Recommendation**: 
  - Make wizard non-dismissible until complete
  - OR: Show persistent banner until onboarding complete
  - Save progress on each step

#### 🟡 **MEDIUM: No Progress Persistence**
- **Problem**: If user closes browser during onboarding, progress is lost
- **Location**: `apps/web/src/components/onboarding/OnboardingWizard.tsx`
- **Impact**: User has to start over
- **Recommendation**: Save progress after each step

#### 🟡 **MEDIUM: Bank Approval Flow Unclear**
- **Problem**: Bank users submit for review but no indication of approval status
- **Location**: `apps/web/src/components/onboarding/OnboardingWizard.tsx:45`
- **Impact**: Bank users may not know their account is pending approval
- **Recommendation**: 
  - Show approval status in dashboard
  - Send email notification when approved
  - Allow admin to approve/reject from admin panel

---

## 4. First-Time Login Experience

### 4.1 Current Flow

1. User logs in (email/password or OAuth)
2. Redirected to dashboard based on role
3. Onboarding wizard shows if `needsOnboarding` is true
4. Dashboard loads

**Issues Identified:**

#### 🟠 **HIGH: No Welcome Screen**
- **Problem**: No welcome message or first-time user guidance
- **Impact**: Users may feel lost
- **Recommendation**: 
  - Show welcome modal for first-time users
  - Highlight key features
  - Offer guided tour

#### 🟡 **MEDIUM: Dashboard May Be Empty**
- **Problem**: New users see empty dashboard with no guidance
- **Impact**: Users may not know what to do next
- **Recommendation**: 
  - Show empty state with call-to-action
  - Suggest first steps (upload document, complete profile, etc.)
  - Show sample data or demo mode

---

## 5. Error Handling

### 5.1 Registration Errors

**Current State**: ✅ **GOOD**
- Password mismatch handled
- Terms agreement checked
- Error messages shown via toast

**Issues:**

#### 🟡 **MEDIUM: Network Errors Not Handled**
- **Problem**: If network fails during registration, user may be stuck
- **Recommendation**: Add retry mechanism and offline detection

#### 🟡 **MEDIUM: Backend Errors Not User-Friendly**
- **Problem**: Backend error messages may be technical
- **Recommendation**: Map backend errors to user-friendly messages

### 5.2 OAuth Errors

**Current State**: ⚠️ **PARTIAL**
- OAuth callback errors handled
- Backend login errors are non-critical (logged but don't fail)

**Issues:**

#### 🔴 **CRITICAL: Backend Login Failure Silent**
- **Problem**: If backend login fails, user sees success but can't use app
- **Location**: `apps/web/src/pages/auth/Callback.tsx:60-63`
- **Recommendation**: Make backend login critical or show warning

---

## 6. Data Consistency Issues

### 6.1 User Data Sync

**Issues:**

#### 🔴 **CRITICAL: Supabase and Backend User Out of Sync**
- **Problem**: User may exist in Supabase but not backend (or vice versa)
- **Impact**: Authentication succeeds but API calls fail
- **Recommendation**: 
  - Ensure user creation is atomic
  - Add sync mechanism
  - Add health check endpoint

#### 🟠 **HIGH: Onboarding Data May Be Incomplete**
- **Problem**: If onboarding progress update fails, user data is incomplete
- **Recommendation**: 
  - Make onboarding progress critical
  - Add validation before marking onboarding complete
  - Show incomplete data warnings

---

## 7. Security Concerns

### 7.1 Password Security

**Issues:**

#### 🟡 **MEDIUM: No Password Strength Validation**
- **Recommendation**: Add password strength meter

#### 🟡 **MEDIUM: Password Truncation**
- **Problem**: Passwords >72 chars are truncated silently
- **Location**: `apps/api/app/routers/auth.py:47`
- **Recommendation**: Show warning if password is too long

### 7.2 OAuth Security

**Issues:**

#### 🟡 **MEDIUM: Token Validation May Fail**
- **Problem**: If Auth0 token validation fails, user may still have Supabase session
- **Recommendation**: Ensure token validation is robust

---

## 8. Recommendations Summary

### Priority 1 (Critical - Fix Immediately)

1. **Fix Dual User Creation**
   - Choose single source of truth (Supabase OR backend)
   - Ensure user exists in both systems synchronously

2. **Handle Email Verification**
   - Check Supabase email confirmation setting
   - Show appropriate UI based on setting
   - Add email verification status check

3. **Make Backend Login Critical for OAuth**
   - Fail OAuth flow if backend login fails
   - OR: Ensure backend user creation happens automatically

4. **Initialize Onboarding for OAuth Users**
   - Check onboarding status after OAuth login
   - Show onboarding wizard if needed

5. **Fix Backend User Creation**
   - Ensure backend user is created during registration
   - OR: Create user on first `/auth/me` call

### Priority 2 (High - Fix Soon)

6. **Add Welcome Screen for First-Time Users**
7. **Make Onboarding Wizard Non-Dismissible**
8. **Show Approval Status for Bank Users**
9. **Handle Onboarding Progress Update Failures**
10. **Add Email Verification Resend Functionality**
11. **Improve Error Messages**
12. **Add Password Strength Validation**
13. **Persist Onboarding Progress**

### Priority 3 (Medium - Nice to Have)

14. **Add Guided Tour**
15. **Show Empty State Guidance**
16. **Add Network Error Retry**
17. **Improve Role Mapping for "Both" Users**
18. **Add User Data Sync Health Check**

---

## 9. Testing Checklist

### Registration Flow
- [ ] Email/password registration creates user in both systems
- [ ] OAuth registration creates user in both systems
- [ ] Email verification flow works (if enabled)
- [ ] Onboarding wizard shows after registration
- [ ] Onboarding progress is saved correctly
- [ ] Error handling works for all failure cases

### OAuth Flow
- [ ] Google OAuth creates backend user
- [ ] Auth0 OAuth creates backend user
- [ ] OAuth users see onboarding wizard
- [ ] OAuth callback errors are handled

### Onboarding Flow
- [ ] Wizard shows for new users
- [ ] Wizard can't be dismissed until complete
- [ ] Progress is saved after each step
- [ ] Bank users see approval status
- [ ] Non-bank users complete immediately

### Error Handling
- [ ] Network errors are handled gracefully
- [ ] Backend errors show user-friendly messages
- [ ] Partial failures don't leave user in bad state

---

## 10. Implementation Plan

### Phase 1: Critical Fixes (Week 1)
1. Fix dual user creation issue
2. Implement email verification flow
3. Make backend login critical for OAuth
4. Initialize onboarding for OAuth users

### Phase 2: High Priority (Week 2)
5. Add welcome screen
6. Make onboarding wizard non-dismissible
7. Improve error handling
8. Add password strength validation

### Phase 3: Polish (Week 3)
9. Add guided tour
10. Improve empty states
11. Add user data sync health check
12. Add comprehensive testing

---

## Conclusion

The onboarding flow has a solid foundation but needs critical fixes to ensure data consistency and user experience. The most critical issues are:

1. **Dual user creation** leading to data inconsistency
2. **Missing email verification** handling
3. **OAuth users** not getting proper onboarding
4. **Silent failures** in backend user creation

Addressing these issues will significantly improve the user onboarding experience and reduce support burden.

