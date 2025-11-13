# Onboarding & Dashboard Regression Checklist

**Updated:** 2025-01-12  
**Scope:** Company size-aware onboarding, combined SME dashboard, enterprise tenant admin dashboard

---

## 1. Registration Flow

### 1.1 SME Exporter
- [ ] Select `Exporter` company type and register
- [ ] Confirm no company size selector is shown
- [ ] Verify redirect to `/lcopilot/exporter-dashboard`
- [ ] Confirm onboarding status is complete

### 1.2 SME Importer
- [ ] Select `Importer` company type and register
- [ ] Confirm no company size selector is shown
- [ ] Verify redirect to `/lcopilot/importer-dashboard`
- [ ] Confirm onboarding status is complete

### 1.3 SME Both (1-20 employees)
- [ ] Select `Both Exporter & Importer`
- [ ] Confirm company size dropdown appears and requires selection
- [ ] Choose `SME (1-20 employees)`
- [ ] Verify redirect to `/lcopilot/combined-dashboard`
- [ ] Confirm onboarding status shows `complete: true`

### 1.4 Medium Enterprise (21-50 employees)
- [ ] Select `Both Exporter & Importer`
- [ ] Choose `Medium Enterprise (21-50 employees)`
- [ ] Verify backend role is `tenant_admin`
- [ ] Confirm redirect to `/lcopilot/enterprise-dashboard`
- [ ] Ensure onboarding status is incomplete with step `team_setup`

### 1.5 Large Enterprise (50+ employees)
- [ ] Repeat flow selecting `Large Enterprise (50+ employees)`
- [ ] Confirm redirect to `/lcopilot/enterprise-dashboard`
- [ ] Confirm onboarding status `team_setup`

### 1.6 Bank
- [ ] Select `Bank`
- [ ] Confirm no FI option exists
- [ ] Verify redirect to `/lcopilot/bank-dashboard`
- [ ] Ensure onboarding status is incomplete with step `kyc`

---

## 2. Login Routing

- [ ] Login as SME exporter → `/lcopilot/exporter-dashboard`
- [ ] Login as SME importer → `/lcopilot/importer-dashboard`
- [ ] Login as SME both (1-20) → `/lcopilot/combined-dashboard`
- [ ] Login as tenant admin (medium/large) → `/lcopilot/enterprise-dashboard`
- [ ] Login as bank officer → `/lcopilot/bank-dashboard`
- [ ] Logout redirects to `/login`

---

## 3. Combined Dashboard (SME Both)

- [ ] Header displays unified messaging and stats
- [ ] Quick actions link to export/import upload pages
- [ ] Tabs render export and import session cards
- [ ] Upcoming deliverables and performance snapshot visible
- [ ] Analytics CTA opens `/lcopilot/analytics`

---

## 4. Enterprise Dashboard (Tenant Admin)

- [ ] Workspace metrics render four summary cards
- [ ] Team workspace cards show members/tasks and CTAs
- [ ] Bank relationship snapshot present
- [ ] Activity tab lists recent cross-team events
- [ ] Governance panel displays approval, retention, audit info

---

## 5. API & Backend

- [ ] `/onboarding/progress` persists `company.size`
- [ ] `onboarding_data.company.size` stored for tenant admin users
- [ ] `_requirements_for_user` includes `company_size` for tenant admins
- [ ] Existing exporters/importers unaffected (defaults to `sme`)

---

## 6. Documentation

- [ ] `docs/USER_TYPE_FLOWS.md` reflects decisions
- [ ] `docs/USER_TYPE_IMPLEMENTATION_PLAN.md` matches implementation
- [ ] Product copy references banks (no FI wording)

---

## Notes

- Supabase Auth must be configured with Auth0 enabled (domain only)
- Render backend requires `AUTH0_*` env vars if Auth0 login is used
- Temporary dashboards use mock/stateless data; integration with live services is tracked separately
