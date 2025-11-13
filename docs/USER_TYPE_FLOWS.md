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
- **Status**: ❌ **REMOVED** - Not supported in current version

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

**✅ DECISION**: Removed from supported user types. Not needed in current version.

---

## Gap Analysis

### Critical Gaps

#### 1. Missing Roles
- ⚠️ `tenant_admin` - Not properly assigned for "both" Medium/Large Enterprise users
- ✅ `consultant` - **REMOVED** (not supported)

#### 2. Missing Company Types
- ⚠️ `financial_institute` - Needs to be distinguished from `bank` (use company_type field)
- ⚠️ `both` - Exists but incorrectly mapped (only Medium/Large should be tenant_admin)

#### 3. Missing Company Size Field
- ❌ **CRITICAL**: No company size field to distinguish SME vs Medium vs Large
- ❌ Can't determine if "both" user should be `exporter` or `tenant_admin`
- ❌ Can't apply appropriate feature limits

#### 4. Missing Onboarding Flows
- ❌ Enterprise onboarding (team setup for Medium/Large)
- ✅ Consultant onboarding - **REMOVED**
- ⚠️ Financial Institute onboarding - Uses same as Bank (acceptable)

#### 5. Missing Dashboards
- ❌ Enterprise Dashboard (for tenant_admin users)
- ✅ Consultant Dashboard - **REMOVED**

#### 6. Role Mapping Issues
- ❌ "both" → "exporter" (should be "tenant_admin" for Medium/Large only)
- ✅ "consultant" → "exporter" - **REMOVED** (consultant option removed)

---

## Required Changes

### Phase 1: Add Company Size Field (CRITICAL)

**New Field in Registration:**
- Add company size dropdown: **SME (20-200)**, **Medium (200-1000)**, **Large (1000+)**
- **Required** when company type is "both"
- Store in `onboarding_data.company_size`
- Use to determine:
  - **Role assignment**: SME "both" → `exporter`, Medium/Large "both" → `tenant_admin`
  - **Feature limits**: SME (basic), Medium (enhanced), Large (unlimited)
  - **Onboarding flow**: SME (simple), Medium/Large (team setup)

### Phase 2: Fix Role Mapping

**File**: `apps/web/src/pages/Register.tsx`

```typescript
// Conditional role mapping based on company size
const getRoleForCompanyType = (companyType: string, companySize?: string): string => {
  if (companyType === "both") {
    // Only Medium/Large enterprises get tenant_admin
    if (companySize === "medium" || companySize === "large") {
      return "tenant_admin";
    }
    // SME "both" users remain as exporter with both business types
    return "exporter";
  }
  
  const roleMap: Record<string, string> = {
    exporter: "exporter",
    importer: "importer",
    bank: "bank_officer",
  };
  return roleMap[companyType] || "exporter";
};
```

### Phase 3: Add Financial Institute Distinction

**New Field in Registration (for Bank/FI):**
- Add institution type dropdown: **Bank** or **Financial Institute**
- Store in `onboarding_data.institution_type`
- Store in `company.type` as `bank` or `financial_institute`
- Use same roles (`bank_officer` / `bank_admin`) but allow future feature differentiation

### Phase 4: Add Enterprise Features

**For `tenant_admin` role (Medium/Large Enterprise):**
- Team management UI
- Workspace sharing
- Multi-user permissions
- Enterprise dashboard
- Enhanced onboarding flow

### Phase 5: Implement Company Size-Based Features

**Feature Limits by Company Size:**
- **SME**: Basic features, limited quotas (e.g., 50 validations/month)
- **Medium**: Enhanced features, higher quotas (e.g., 500 validations/month), team management
- **Large**: All features, unlimited quotas, advanced team management, dedicated support

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
[ ] Bank / Financial Institute
```

### Step 3: Company Size (REQUIRED if "Both Exporter & Importer")
```
How many employees does your company have?

[ ] SME (20-200 employees)
[ ] Medium Enterprise (200-1000 employees)
[ ] Large Enterprise (1000+ employees)
```

**Note**: Company size is **required** for "Both Exporter & Importer" to determine role assignment.

### Step 4: Additional Information (if Bank/FI)
- Institution type: **Bank** or **Financial Institute** (dropdown)
- Regulator ID (required for banks, optional for FIs)

### Step 5: Terms & Conditions
- Terms agreement checkbox

---

## Onboarding Flow Matrix

| User Type | Role | Company Size | Onboarding Required | KYC Required | Approval Required | Dashboard |
|-----------|------|--------------|---------------------|--------------|-------------------|-----------|
| SME Exporter | `exporter` | SME | No | No | No | ExporterDashboardV2 |
| SME Importer | `importer` | SME | No | No | No | ImporterDashboardV2 |
| SME (Both) | `exporter` | SME | No | No | No | ExporterDashboardV2 |
| Medium Enterprise (Both) | `tenant_admin` | Medium | Yes (team setup) | No | No | Enterprise Dashboard ⚠️ |
| Large Enterprise (Both) | `tenant_admin` | Large | Yes (team setup) | No | No | Enterprise Dashboard ⚠️ |
| Bank | `bank_officer` | N/A | Yes (KYC) | Yes | Yes | BankDashboardV2 |
| Financial Institute | `bank_officer` | N/A | Yes (KYC) | Yes | Yes | BankDashboardV2 |

---

## Implementation Priority

### Priority 1: Critical Fixes (Must Do First)
1. ✅ **Add company size field** - Required to determine role assignment
2. ✅ **Fix "both" → `tenant_admin` mapping** - Only for Medium/Large, conditional on company size
3. ✅ **Add institution type field** - For Bank/FI distinction
4. ✅ **Update registration form** - Add company size dropdown, make conditional

### Priority 2: Enterprise Features
5. ⏳ **Create Enterprise Dashboard** - For `tenant_admin` users
6. ⏳ **Update onboarding wizard** - Different flow for Medium/Large Enterprise
7. ⏳ **Enterprise team management UI** - Workspace sharing, multi-user access

### Priority 3: Feature Limits by Company Size
8. ⏳ **Implement quota system** - Based on company size
9. ⏳ **Feature gating** - SME (basic), Medium (enhanced), Large (unlimited)
10. ⏳ **Analytics by company size** - Track usage patterns

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

## Decisions Made ✅

1. **Enterprise Users**: ✅ **DECIDED** - Only Medium & Large Enterprises get `tenant_admin` role. SMEs selecting "both" remain as `exporter` with `business_types: ['exporter', 'importer']`.

2. **Financial Institutes**: ✅ **RECOMMENDED** - Use `bank_officer` / `bank_admin` roles with `company_type: 'financial_institute'` field to distinguish. Keeps it simple, allows future differentiation.

3. **Consultants**: ✅ **DECIDED** - Removed from supported user types.

4. **Company Size**: ✅ **DECIDED** - Should affect features/limits:
   - **SME**: Basic features, limited quotas (e.g., 50 validations/month)
   - **Medium**: Enhanced features, higher quotas (e.g., 500 validations/month), team management
   - **Large**: All features, unlimited quotas, advanced team management, dedicated support
   - Also used for analytics and business intelligence

5. **SME vs Enterprise**: ✅ **RECOMMENDED** - Different onboarding flows:
   - **SME**: Simple, quick onboarding (skip wizard, immediate access)
   - **Medium/Large Enterprise**: Enhanced onboarding with team setup wizard
   - Different post-onboarding features based on company size

