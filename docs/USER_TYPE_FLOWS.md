# User Type Flow Design & Gap Analysis

**Date**: 2025-01-12  
**Purpose**: Define proper onboarding and post-onboarding flows for each user type before fixing onboarding implementation

---

## User Type Categories

### 1. SME Exporters
- **Profile**: Small to medium exporters (20-200 employees)
- **Role**: `exporter`
- **Company Type**: `exporter`
- **Business Types**: `['exporter']`
- **Onboarding**: Simple, self-service
- **KYC**: Not required

### 2. SME Importers
- **Profile**: Small to medium importers (20-200 employees)
- **Role**: `importer`
- **Company Type**: `importer`
- **Business Types**: `['importer']`
- **Onboarding**: Simple, self-service
- **KYC**: Not required

### 3. Medium/Large Enterprise (Both Exporter & Importer)
- **Profile**: Medium to large enterprises that do both exporting and importing
- **Role**: `tenant_admin` ⚠️ **CURRENTLY MISSING**
- **Company Type**: `both`
- **Business Types**: `['exporter', 'importer']`
- **Onboarding**: Enhanced with team management
- **KYC**: May be required for large enterprises
- **Features**: Team management, workspace sharing, multi-user access

### 4. Banks
- **Profile**: Commercial banks, trade finance departments
- **Role**: `bank_officer` or `bank_admin`
- **Company Type**: `bank`
- **Business Types**: N/A (banks don't trade)
- **Onboarding**: Requires KYC approval
- **KYC**: **REQUIRED** - Must be approved by system admin
- **Features**: Compliance monitoring, audit trails, client management

### 5. Financial Institutes (Non-Bank FIs)
- **Profile**: Non-bank financial institutions (factoring companies, trade finance companies, etc.)
- **Role**: ⚠️ **CURRENTLY MISSING** - Should be `fi_officer` or `fi_admin`
- **Company Type**: ⚠️ **CURRENTLY MISSING** - Should be `financial_institute`
- **Business Types**: N/A
- **Onboarding**: Requires KYC approval (similar to banks)
- **KYC**: **REQUIRED**
- **Features**: Similar to banks but may have different compliance requirements

### 6. Trade Consultants
- **Profile**: Independent trade finance consultants
- **Role**: ⚠️ **CURRENTLY MISSING** - Should be `consultant`
- **Company Type**: `consultant`
- **Business Types**: N/A
- **Onboarding**: Simple, self-service
- **KYC**: Not required (or simplified)
- **Features**: May need to manage multiple client workspaces

---

## Current State Analysis

### Registration Form Issues

**Location**: `apps/web/src/pages/Register.tsx`

**Current Company Types:**
```typescript
const COMPANY_TYPES = [
  { value: "exporter", label: "Exporter" },
  { value: "importer", label: "Importer" },
  { value: "both", label: "Both Exporter & Importer" },
  { value: "bank", label: "Bank / FI" },
  { value: "consultant", label: "Trade Consultant" },
];
```

**Current Role Mapping:**
```typescript
const roleMap: Record<string, string> = {
  exporter: "exporter",      // ✅ Correct
  importer: "importer",      // ✅ Correct
  both: "exporter",          // ❌ WRONG - Should be "tenant_admin"
  bank: "bank_officer",       // ✅ Correct
  consultant: "exporter",     // ❌ WRONG - Should be "consultant"
};
```

**Issues:**
1. ❌ **"both" maps to "exporter"** - Should map to `tenant_admin`
2. ❌ **"consultant" maps to "exporter"** - Should map to `consultant` role
3. ❌ **No distinction between SME and Enterprise** - "both" could be SME or Enterprise
4. ❌ **No Financial Institute option** - Banks and FIs are grouped together
5. ❌ **No company size question** - Can't differentiate SME vs Enterprise

---

## Required Flow Designs

### Flow 1: SME Exporter

#### Registration Flow
1. **Registration Form**
   - Company name
   - Contact person (full name)
   - Business email
   - Password
   - Company type: **Exporter**
   - **NEW**: Company size: **SME** (20-200 employees)
   - Terms agreement

2. **Backend Processing**
   - Role: `exporter`
   - Company type: `exporter`
   - Business types: `['exporter']`
   - Company size: `sme` (new field needed)
   - Onboarding: `complete: true` (no KYC needed)
   - Status: `approved`

3. **Post-Registration**
   - Redirect to: `/dashboard` (Exporter Dashboard)
   - Onboarding wizard: **Skip** (already complete)
   - Welcome message: "Welcome! Start validating your LC documents"

#### Onboarding Checklist
- ✅ Account created
- ✅ Email verified (if required)
- ✅ Company profile created
- ✅ Ready to use

#### Post-Onboarding Experience
- **Dashboard**: ExporterDashboardV2
- **Features**: Upload LC, validate documents, view results, analytics
- **Limitations**: Own data only, no team management

---

### Flow 2: SME Importer

#### Registration Flow
1. **Registration Form**
   - Company name
   - Contact person (full name)
   - Business email
   - Password
   - Company type: **Importer**
   - **NEW**: Company size: **SME** (20-200 employees)
   - Terms agreement

2. **Backend Processing**
   - Role: `importer`
   - Company type: `importer`
   - Business types: `['importer']`
   - Company size: `sme`
   - Onboarding: `complete: true`
   - Status: `approved`

3. **Post-Registration**
   - Redirect to: `/dashboard` (Importer Dashboard)
   - Onboarding wizard: **Skip**
   - Welcome message: "Welcome! Start validating your LC drafts"

#### Onboarding Checklist
- ✅ Account created
- ✅ Email verified
- ✅ Company profile created
- ✅ Ready to use

#### Post-Onboarding Experience
- **Dashboard**: ImporterDashboardV2
- **Features**: Upload LC drafts, validate terms, view results, analytics
- **Limitations**: Own data only, no team management

---

### Flow 3: Medium/Large Enterprise (Both Exporter & Importer)

#### Registration Flow
1. **Registration Form**
   - Company name
   - Contact person (full name)
   - Business email
   - Password
   - Company type: **Both Exporter & Importer**
   - **NEW**: Company size: **Medium** (200-1000 employees) or **Large** (1000+ employees)
   - Terms agreement

2. **Backend Processing**
   - Role: `tenant_admin` ⚠️ **NEEDS FIX**
   - Company type: `both`
   - Business types: `['exporter', 'importer']`
   - Company size: `medium` or `large`
   - Onboarding: `complete: false` (needs team setup)
   - Status: `approved`
   - **NEW**: Features enabled: Team management, workspace sharing

3. **Post-Registration**
   - Redirect to: `/dashboard` (Enterprise Dashboard - needs to be created)
   - Onboarding wizard: **Show** (for team setup)
   - Welcome message: "Welcome! Let's set up your team workspace"

#### Onboarding Checklist
- ✅ Account created
- ✅ Email verified
- ✅ Company profile created
- ⏳ **Team setup** (onboarding wizard)
  - Invite team members
  - Set up workspaces
  - Configure permissions
- ✅ Ready to use

#### Post-Onboarding Experience
- **Dashboard**: Enterprise Dashboard (needs to be created)
- **Features**: 
  - All exporter features
  - All importer features
  - Team management
  - Workspace sharing
  - Multi-user access
  - Role-based permissions within company
- **Limitations**: Company-scoped data only

---

### Flow 4: Bank

#### Registration Flow
1. **Registration Form**
   - Bank name
   - Contact person (full name, title)
   - Business email (bank domain)
   - Password
   - Company type: **Bank / FI**
   - **NEW**: Institution type: **Bank** or **Financial Institute**
   - **NEW**: Regulator ID (required for banks)
   - Terms agreement

2. **Backend Processing**
   - Role: `bank_officer` (first user) or `bank_admin` (if specified)
   - Company type: `bank`
   - Business types: N/A
   - Onboarding: `complete: false`
   - Onboarding step: `kyc`
   - Status: `pending` (requires approval)
   - KYC required: `true`
   - KYC status: `pending`

3. **Post-Registration**
   - Redirect to: `/dashboard` (Bank Dashboard - limited access)
   - Onboarding wizard: **Show** (KYC submission)
   - Welcome message: "Welcome! Please complete KYC verification to access all features"
   - **Status Banner**: "Account pending approval"

#### Onboarding Checklist
- ✅ Account created
- ✅ Email verified
- ✅ Company profile created
- ⏳ **KYC Submission** (onboarding wizard)
  - Upload regulatory documents
  - Provide regulator ID
  - Submit for review
- ⏳ **Admin Approval** (system admin reviews)
- ✅ Account approved
- ✅ Ready to use

#### Post-Onboarding Experience
- **Dashboard**: BankDashboardV2
- **Features**: 
  - View all validation sessions (system-wide)
  - Compliance monitoring
  - Audit trails
  - Client management
  - Bulk processing
  - SLA dashboards
  - Evidence packs
- **Limitations**: Read-only for validation (can't create validation sessions)

---

### Flow 5: Financial Institute (Non-Bank)

#### Registration Flow
1. **Registration Form**
   - Institution name
   - Contact person (full name, title)
   - Business email
   - Password
   - Company type: **Bank / FI** ⚠️ **NEEDS SEPARATE OPTION**
   - **NEW**: Institution type: **Financial Institute**
   - **NEW**: Regulator ID (if applicable)
   - Terms agreement

2. **Backend Processing**
   - Role: ⚠️ **NEEDS NEW ROLE** `fi_officer` or `fi_admin`
   - Company type: ⚠️ **NEEDS NEW TYPE** `financial_institute`
   - Business types: N/A
   - Onboarding: `complete: false`
   - Onboarding step: `kyc`
   - Status: `pending`
   - KYC required: `true`
   - KYC status: `pending`

3. **Post-Registration**
   - Similar to Bank flow but may have different compliance requirements

#### Onboarding Checklist
- Similar to Bank but may have different KYC requirements

#### Post-Onboarding Experience
- Similar to Bank but may have different features/permissions

---

### Flow 6: Trade Consultant

#### Registration Flow
1. **Registration Form**
   - Consultant name / Company name
   - Contact person (full name)
   - Business email
   - Password
   - Company type: **Trade Consultant**
   - Terms agreement

2. **Backend Processing**
   - Role: ⚠️ **NEEDS NEW ROLE** `consultant`
   - Company type: `consultant`
   - Business types: N/A
   - Onboarding: `complete: true` (or simplified)
   - Status: `approved`

3. **Post-Registration**
   - Redirect to: `/dashboard` (Consultant Dashboard - needs to be created)
   - Onboarding wizard: **Skip** or **Simplified**
   - Welcome message: "Welcome! Set up your consultant profile"

#### Onboarding Checklist
- ✅ Account created
- ✅ Email verified
- ✅ Profile created
- ⏳ **Client workspace setup** (optional)
- ✅ Ready to use

#### Post-Onboarding Experience
- **Dashboard**: Consultant Dashboard (needs to be created)
- **Features**: 
  - May need to manage multiple client workspaces
  - View client validation sessions (with permission)
  - Provide consulting services
- **Limitations**: Depends on client permissions

---

## Gap Analysis

### Critical Gaps

#### 1. Missing Roles
- ❌ `tenant_admin` - Not properly assigned for "both" users
- ❌ `consultant` - Not implemented
- ❌ `fi_officer` / `fi_admin` - Not implemented

#### 2. Missing Company Types
- ❌ `financial_institute` - Grouped with banks
- ⚠️ `both` - Exists but incorrectly mapped

#### 3. Missing Company Size Field
- ❌ No distinction between SME and Enterprise
- ❌ Can't differentiate Medium vs Large Enterprise

#### 4. Missing Onboarding Flows
- ❌ Enterprise onboarding (team setup)
- ❌ Consultant onboarding
- ❌ Financial Institute onboarding (separate from bank)

#### 5. Missing Dashboards
- ❌ Enterprise Dashboard (for tenant_admin users)
- ❌ Consultant Dashboard

#### 6. Role Mapping Issues
- ❌ "both" → "exporter" (should be "tenant_admin")
- ❌ "consultant" → "exporter" (should be "consultant")

---

## Required Changes

### Phase 1: Fix Role Mapping

**File**: `apps/web/src/pages/Register.tsx`

```typescript
const roleMap: Record<string, string> = {
  exporter: "exporter",
  importer: "importer",
  both: "tenant_admin",        // ✅ FIX: Map to tenant_admin
  bank: "bank_officer",
  consultant: "consultant",     // ✅ FIX: Map to consultant (needs backend support)
};
```

### Phase 2: Add Company Size Field

**New Field in Registration:**
- Add company size dropdown: SME (20-200), Medium (200-1000), Large (1000+)
- Store in `onboarding_data.company_size`
- Use to determine features/limits

### Phase 3: Separate Financial Institute

**New Company Type:**
- Add `financial_institute` to COMPANY_TYPES
- Create `fi_officer` and `fi_admin` roles in backend
- Separate onboarding flow if needed

### Phase 4: Add Enterprise Features

**For `tenant_admin` role:**
- Team management UI
- Workspace sharing
- Multi-user permissions
- Enterprise dashboard

### Phase 5: Add Consultant Role

**Backend:**
- Add `consultant` role to UserRole enum
- Add permissions for consultant role
- Create consultant dashboard

---

## Recommended Registration Form Structure

### Step 1: Basic Information
- Company/Institution name
- Contact person name
- Business email
- Password
- Confirm password

### Step 2: Business Type Selection
```
What best describes your business?

[ ] Exporter only
[ ] Importer only  
[ ] Both Exporter & Importer
[ ] Bank
[ ] Financial Institute (Non-Bank)
[ ] Trade Consultant
```

### Step 3: Company Size (if SME/Enterprise)
```
How many employees does your company have?

[ ] SME (20-200 employees)
[ ] Medium Enterprise (200-1000 employees)
[ ] Large Enterprise (1000+ employees)
```

### Step 4: Additional Information (if Bank/FI)
- Regulator ID (required)
- Institution type (Bank vs Financial Institute)

### Step 5: Terms & Conditions
- Terms agreement checkbox

---

## Onboarding Flow Matrix

| User Type | Role | Onboarding Required | KYC Required | Approval Required | Dashboard |
|-----------|------|---------------------|--------------|-------------------|-----------|
| SME Exporter | `exporter` | No | No | No | ExporterDashboardV2 |
| SME Importer | `importer` | No | No | No | ImporterDashboardV2 |
| Enterprise (Both) | `tenant_admin` | Yes (team setup) | Maybe | No | Enterprise Dashboard ⚠️ |
| Bank | `bank_officer` | Yes (KYC) | Yes | Yes | BankDashboardV2 |
| Financial Institute | `fi_officer` ⚠️ | Yes (KYC) | Yes | Yes | FI Dashboard ⚠️ |
| Consultant | `consultant` ⚠️ | Simplified | No | No | Consultant Dashboard ⚠️ |

---

## Implementation Priority

### Priority 1: Critical Fixes
1. ✅ Fix "both" → `tenant_admin` mapping
2. ✅ Add company size field
3. ✅ Create Enterprise Dashboard
4. ✅ Update onboarding wizard for enterprise users

### Priority 2: New Roles
5. ⏳ Add `consultant` role
6. ⏳ Add `fi_officer` / `fi_admin` roles
7. ⏳ Separate Financial Institute from Bank

### Priority 3: Enhanced Features
8. ⏳ Enterprise team management UI
9. ⏳ Consultant dashboard
10. ⏳ FI-specific features (if different from banks)

---

## Next Steps

1. **Review this document** - Confirm user type definitions
2. **Prioritize implementations** - Which flows are most critical?
3. **Design Enterprise Dashboard** - What should it look like?
4. **Design Consultant Dashboard** - What features needed?
5. **Update registration form** - Add company size, fix role mapping
6. **Update backend** - Add missing roles, update role mapping
7. **Create onboarding flows** - Enterprise, Consultant, FI-specific
8. **Test each flow** - Ensure proper end-to-end experience

---

## Questions to Answer

1. **Enterprise Users**: Should "both exporter & importer" always be `tenant_admin`, or only for Medium/Large enterprises?
2. **Financial Institutes**: Are FIs different enough from banks to warrant separate role, or can they use `bank_officer`?
3. **Consultants**: Do consultants need their own dashboard, or can they use exporter/importer dashboards with different permissions?
4. **Company Size**: Should company size affect features/limits, or just for analytics?
5. **SME vs Enterprise**: Should there be different onboarding flows, or just different post-onboarding features?

