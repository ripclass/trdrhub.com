# User Type Flow Implementation Plan

**Date**: 2025-01-12  
**Status**: Ready for Implementation  
**Based on**: `docs/USER_TYPE_FLOWS.md`

---

## Decisions Summary

✅ **Enterprise Users**: Only Medium & Large Enterprises get `tenant_admin` role  
✅ **Financial Institutes**: Removed - FIs act as consultants and don't check LCs themselves  
✅ **Consultants**: Removed from supported types  
✅ **Company Size**: Affects features, limits, and onboarding flow  
   - **SME**: 1-20 employees
   - **Medium**: 21-50 employees  
   - **Large**: 50+ employees
✅ **SME vs Enterprise**: Different onboarding flows  
✅ **Combined Dashboard**: Required for users who do both exporting and importing
   - **SME "both"**: Unified combined view (export + import together)
   - **Medium/Large Enterprise**: Enhanced dashboard with advanced filtering and team features

---

## Implementation Steps

### Step 1: Add Company Size Field to Registration Form

**File**: `apps/web/src/pages/Register.tsx`

**Changes:**
1. Add company size state:
```typescript
const [companySize, setCompanySize] = useState<string>("");
```

2. Add company size dropdown (shown when companyType === "both"):
```tsx
{formData.companyType === "both" && (
  <div className="space-y-2 sm:col-span-2">
    <Label htmlFor="companySize">Company size</Label>
    <Select
      value={companySize}
      onValueChange={(value) => setCompanySize(value)}
      required
    >
      <SelectTrigger className="h-11">
        <SelectValue placeholder="Select company size" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="sme">SME (1-20 employees)</SelectItem>
        <SelectItem value="medium">Medium Enterprise (21-50 employees)</SelectItem>
        <SelectItem value="large">Large Enterprise (50+ employees)</SelectItem>
      </SelectContent>
    </Select>
    <p className="text-xs text-muted-foreground">
      Company size determines available features and team management capabilities.
    </p>
  </div>
)}
```

3. Remove institution type field (FI option removed):
```tsx
// REMOVED - No longer needed since FI option is removed
// Only banks register, no need to distinguish Bank vs FI
```

4. Update validation:
```typescript
if (formData.companyType === "both" && !companySize) {
  toast({
    title: "Company size required",
    description: "Please select your company size to continue.",
    variant: "destructive",
  });
  setIsLoading(false);
  return;
}
```

5. Update role assignment logic:
```typescript
const getBackendRole = (companyType: string, companySize?: string): string => {
  if (companyType === "both") {
    // Only Medium/Large enterprises get tenant_admin
    if (companySize === "medium" || companySize === "large") {
      return "tenant_admin";
    }
    // SME "both" users remain as exporter
    return "exporter";
  }
  
  const roleMap: Record<string, string> = {
    exporter: "exporter",
    importer: "importer",
    bank: "bank_officer",
  };
  return roleMap[companyType] || "exporter";
};

const backendRole = getBackendRole(formData.companyType, companySize);
```

6. Update onboarding progress call:
```typescript
await updateProgress({
  role: backendRole,
  company: { 
    name: formData.companyName, 
    type: formData.companyType,
    size: companySize, // NEW
    institution_type: institutionType, // NEW (if bank/FI)
  },
  business_types: businessTypes,
  complete: !isBank && companySize !== "medium" && companySize !== "large", // Enterprise needs onboarding
  onboarding_step: isBank ? 'kyc' : (companySize === "medium" || companySize === "large") ? 'team_setup' : null,
})
```

---

### Step 2: Update Backend Schema

**File**: `apps/api/app/schemas/onboarding.py`

**Changes:**
1. Add company size to CompanyPayload:
```python
class CompanyPayload(BaseModel):
    name: str
    type: str
    legal_name: Optional[str] = None
    registration_number: Optional[str] = None
    regulator_id: Optional[str] = None
    country: Optional[str] = None
    size: Optional[str] = Field(None, description="Company size: sme, medium, large")  # NEW
    institution_type: Optional[str] = Field(None, description="Bank or Financial Institute")  # NEW
```

2. Store company size in onboarding_data:
```python
if payload.company:
    company = _ensure_company(db, current_user, payload.company)
    onboarding_data = {
        "company": {
            "name": company.name,
            "type": payload.company.type,
            "size": payload.company.size,  # NEW
            "institution_type": payload.company.institution_type,  # NEW
            # ... rest of company data
        }
    }
    _persist_onboarding_data(current_user, onboarding_data)
```

---

### Step 3: Update Company Model (Optional)

**File**: `apps/api/app/models/company.py`

**Consider adding:**
- `company_size` column (sme, medium, large)
- `institution_type` column (bank, financial_institute)

**OR** store in `onboarding_data` JSONB field (simpler, no migration needed)

---

### Step 4: Update Onboarding Wizard

**File**: `apps/web/src/components/onboarding/OnboardingWizard.tsx`

**Changes:**
1. Add team setup step for Medium/Large Enterprise:
```typescript
type WizardStep = 'role' | 'company' | 'business' | 'team_setup' | 'review' | 'complete'

const determineInitialStep = (): WizardStep => {
  if (!status || !status.role) return 'role'
  if (!status.company_id) return 'company'
  
  // Enterprise users need team setup
  if (status.role === 'tenant_admin') {
    const companySize = status.details?.company?.size
    if (companySize === 'medium' || companySize === 'large') {
      return status.completed ? 'complete' : 'team_setup'
    }
  }
  
  // Bank users need KYC
  if (isBankRole(status.role)) {
    return status.completed ? 'complete' : waitingForApproval ? 'review' : 'company'
  }
  
  return status.completed ? 'complete' : 'business'
}
```

2. Add team setup step component (new file needed):
- Invite team members
- Set up workspaces
- Configure permissions

---

### Step 5: Create Combined/Enterprise Dashboard

**File**: `apps/web/src/pages/CombinedDashboard.tsx` (new) - For SME "both" users  
**File**: `apps/web/src/pages/EnterpriseDashboard.tsx` (new) - For Medium/Large Enterprise

**Combined Dashboard (SME "both" users):**
- **Unified View**: Export and import LCs shown together in one interface
- **Why Unified?**
  - SMEs (1-20 employees) typically have one person managing both
  - Lower volume doesn't require separate views
  - Reduces context switching and cognitive load
  - Simpler mental model - "all my LCs in one place"
- **Features**:
  - Single interface showing both export and import LCs
  - Filter by LC type (export/import/both) if needed
  - Can validate both types from same dashboard
  - Basic analytics across all LCs

**Enterprise Dashboard (Medium/Large Enterprise):**
- **Enhanced Combined View**: Advanced filtering and team features
- **Why Advanced?**
  - Medium/Large enterprises have teams managing different aspects
  - Higher volume requires better organization
  - Need workspace separation for departments/projects
  - Team collaboration essential
- **Features**:
  - Unified dashboard with advanced filtering (all/export/import/by workspace/by team)
  - Team management section
  - Workspace sharing (multiple workspaces for departments/projects)
  - Multi-user access controls (role-based permissions)
  - Enhanced analytics (company-wide insights)

**Routing:**
```typescript
// SME "both" users (exporter role with business_types: ['exporter', 'importer'])
if (user.role === "exporter" && user.business_types?.includes("importer")) {
  return "/combined-dashboard";
}

// Medium/Large Enterprise (tenant_admin role)
case "tenant_admin":
  return "/enterprise-dashboard";
```

---

### Step 6: Implement Feature Limits

**File**: `apps/api/app/core/quota.py` (new)

**Quota System:**
```python
def get_quota_limit(company_size: str) -> Optional[int]:
    """Get validation quota limit based on company size."""
    limits = {
        "sme": 50,      # 50 validations per month (1-20 employees)
        "medium": 500,  # 500 validations per month (21-50 employees)
        "large": None,  # Unlimited (50+ employees)
    }
    return limits.get(company_size, 50)

def check_quota(user: User, db: Session) -> bool:
    """Check if user has remaining quota."""
    company_size = user.onboarding_data.get("company", {}).get("size", "sme")
    limit = get_quota_limit(company_size)
    
    if limit is None:
        return True  # Unlimited
    
    # Check current month usage
    current_month_usage = get_monthly_usage(user.company_id, db)
    return current_month_usage < limit
```

---

### Step 7: Update Registration Form Company Types

**File**: `apps/web/src/pages/Register.tsx`

**Remove consultant and FI options:**
```typescript
const COMPANY_TYPES = [
  { value: "exporter", label: "Exporter" },
  { value: "importer", label: "Importer" },
  { value: "both", label: "Both Exporter & Importer" },
  { value: "bank", label: "Bank" },
  // REMOVED: { value: "consultant", label: "Trade Consultant" },
  // REMOVED: { value: "financial_institute", label: "Financial Institute" },
];
```

---

## Testing Checklist

### Registration Tests
- [ ] SME Exporter registration works
- [ ] SME Importer registration works
- [ ] SME "both" registration → `exporter` role
- [ ] Medium "both" registration → `tenant_admin` role
- [ ] Large "both" registration → `tenant_admin` role
- [ ] Bank registration → `bank_officer` role
- [ ] Company size field required for "both"
- [ ] FI option removed from registration form

### Onboarding Tests
- [ ] SME users skip onboarding wizard
- [ ] Medium/Large Enterprise users see team setup wizard
- [ ] Bank users see KYC wizard
- [ ] FI users see KYC wizard (same as bank)

### Dashboard Tests
- [ ] SME exporters → ExporterDashboard
- [ ] SME importers → ImporterDashboardV2
- [ ] SME "both" → ExporterDashboard (can switch views)
- [ ] Medium/Large Enterprise → Enterprise Dashboard
- [ ] Banks → BankDashboardV2
- [ ] FIs → BankDashboardV2

### Feature Limit Tests
- [ ] SME users (1-20 employees) limited to 50 validations/month
- [ ] Medium Enterprise (21-50 employees) limited to 500 validations/month
- [ ] Large Enterprise (50+ employees) unlimited
- [ ] Quota exceeded shows appropriate message

### Combined Dashboard Tests
- [ ] SME "both" users see Combined Dashboard (unified view)
- [ ] Export and import LCs shown together in unified interface
- [ ] Can validate export LCs in combined dashboard
- [ ] Can validate import LCs in combined dashboard
- [ ] Filter by LC type (export/import/both) works correctly
- [ ] Default view shows all LCs together (unified)
- [ ] Medium/Large Enterprise users see Enterprise Dashboard with advanced filtering and team features

---

## Migration Notes

### Database Changes
- No schema changes needed if storing company size in `onboarding_data` JSONB
- If adding columns: `company_size`, `institution_type` to `companies` table

### Backward Compatibility
- Existing users without company size default to "sme"
- Existing "both" users remain as `exporter` (won't break)
- Can migrate existing users later if needed

---

## Rollout Plan

1. **Week 1**: Add company size field, fix role mapping
2. **Week 2**: Create Enterprise Dashboard, update onboarding wizard
3. **Week 3**: Implement feature limits/quota system
4. **Week 4**: Testing and bug fixes
5. **Week 5**: Deploy and monitor

---

## Success Criteria

✅ All user types can register correctly  
✅ Role assignment works based on company size  
✅ Enterprise users get proper onboarding flow  
✅ Feature limits enforced correctly  
✅ All dashboards accessible and functional  
✅ No breaking changes for existing users

