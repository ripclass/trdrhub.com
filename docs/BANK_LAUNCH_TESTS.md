# Bank Dashboard Launch Tests

## ⚠️ IMPORTANT: Do You Need Org Tests?

**If you DON'T have multiple organizations:**
- ✅ That's OK! Org feature is **optional**
- ✅ Use "All Organizations" (default)
- ✅ Skip Test 1 if you're a single-branch bank
- ✅ See `docs/BANK_LAUNCH_TESTS_SIMPLE.md` for simpler tests

**If you DO have multiple organizations:**
- Run Test 1 below to verify org isolation works

---

## Test 1: Org Isolation Test (OPTIONAL - Only if you have orgs)

### Prerequisites
- Two bank organizations created in staging/production
- Two bank users, each assigned to different orgs
- At least 5 validation sessions per org (with different LC numbers)

**Note:** If you don't have orgs yet, skip this test and use "All Organizations" instead.

### Test Steps

#### Setup
1. **Create Test Data**
   ```sql
   -- Create Org 1: "Test Bank - APAC"
   INSERT INTO bank_orgs (id, bank_company_id, parent_id, kind, name, code, path, level, sort_order, is_active)
   VALUES (gen_random_uuid(), '<bank_company_id>', NULL, 'region', 'Test Bank - APAC', 'APAC', '/<org1_id>', 0, 1, true);
   
   -- Create Org 2: "Test Bank - EMEA"
   INSERT INTO bank_orgs (id, bank_company_id, parent_id, kind, name, code, path, level, sort_order, is_active)
   VALUES (gen_random_uuid(), '<bank_company_id>', NULL, 'region', 'Test Bank - EMEA', 'EMEA', '/<org2_id>', 0, 2, true);
   
   -- Assign User 1 to Org 1
   INSERT INTO user_org_access (user_id, org_id, role)
   VALUES ('<user1_id>', '<org1_id>', 'editor');
   
   -- Assign User 2 to Org 2
   INSERT INTO user_org_access (user_id, org_id, role)
   VALUES ('<user2_id>', '<org2_id>', 'editor');
   
   -- Create validation sessions for Org 1 (with org_id in metadata)
   UPDATE validation_sessions 
   SET extracted_data = jsonb_set(
     COALESCE(extracted_data, '{}'::jsonb),
     '{bank_metadata,org_id}',
     to_jsonb('<org1_id>'::text)
   )
   WHERE id IN (<session_ids_for_org1>);
   
   -- Create validation sessions for Org 2 (with org_id in metadata)
   UPDATE validation_sessions 
   SET extracted_data = jsonb_set(
     COALESCE(extracted_data, '{}'::jsonb),
     '{bank_metadata,org_id}',
     to_jsonb('<org2_id>'::text)
   )
   WHERE id IN (<session_ids_for_org2>);
   ```

#### Test Execution

**Test 1.1: Results Page Isolation**
- [ ] Login as User 1 (Org 1)
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=results&org=<org1_id>`
- [ ] Verify only Org 1 sessions are visible
- [ ] Note LC numbers visible: `________________`
- [ ] Switch to Org 2 in org switcher
- [ ] Verify URL updates to `?tab=results&org=<org2_id>`
- [ ] Verify different sessions are shown
- [ ] Verify Org 1 LC numbers are NOT visible
- [ ] Switch to "All Organizations"
- [ ] Verify both orgs' sessions are visible (if user is admin)

**Test 1.2: Approvals Page Isolation**
- [ ] Login as User 1 (Org 1)
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=approvals&org=<org1_id>`
- [ ] Verify only Org 1 approvals are visible
- [ ] Switch to Org 2
- [ ] Verify only Org 2 approvals are visible
- [ ] Verify Org 1 approvals are NOT visible

**Test 1.3: Discrepancies Page Isolation**
- [ ] Login as User 1 (Org 1)
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=discrepancies&org=<org1_id>`
- [ ] Verify only Org 1 discrepancies are visible
- [ ] Switch to Org 2
- [ ] Verify only Org 2 discrepancies are visible

**Test 1.4: Evidence Packs Isolation**
- [ ] Login as User 1 (Org 1)
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=evidence-packs&org=<org1_id>`
- [ ] Verify only Org 1 sessions are listed
- [ ] Switch to Org 2
- [ ] Verify only Org 2 sessions are listed

**Test 1.5: Queue Operations Isolation**
- [ ] Login as User 1 (Org 1)
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=queue&org=<org1_id>`
- [ ] Verify only Org 1 queue jobs are visible
- [ ] Switch to Org 2
- [ ] Verify only Org 2 queue jobs are visible

**Test 1.6: Duplicate Detection Isolation**
- [ ] Login as User 1 (Org 1)
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=results&org=<org1_id>`
- [ ] Open a session detail modal
- [ ] Check duplicate candidates
- [ ] Verify only Org 1 duplicates are shown
- [ ] Switch to Org 2
- [ ] Verify different duplicates are shown (or none if no duplicates)

**Test 1.7: Saved Views Isolation**
- [ ] Login as User 1 (Org 1)
- [ ] Create a saved view on Results page with `org=<org1_id>`
- [ ] Switch to Org 2
- [ ] Verify saved view doesn't show Org 1 data
- [ ] Create a saved view for Org 2
- [ ] Switch back to Org 1
- [ ] Verify Org 2 saved view doesn't show Org 1 data

**Test 1.8: Exports Isolation**
- [ ] Login as User 1 (Org 1)
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=results&org=<org1_id>`
- [ ] Export CSV
- [ ] Verify CSV only contains Org 1 sessions
- [ ] Switch to Org 2
- [ ] Export CSV
- [ ] Verify CSV only contains Org 2 sessions

**Test 1.9: API Direct Access**
- [ ] Login as User 1 (Org 1)
- [ ] Open browser DevTools → Network tab
- [ ] Navigate to Results page
- [ ] Find API call to `/bank/results?org=<org1_id>`
- [ ] Verify response only contains Org 1 sessions
- [ ] Manually change URL to `?org=<org2_id>` (if user has access)
- [ ] Verify response changes to Org 2 sessions
- [ ] If user doesn't have Org 2 access, verify 403 error

**Test 1.10: Cross-Org Data Leakage**
- [ ] Login as User 1 (Org 1)
- [ ] Note a specific LC number from Org 1: `LC-ORG1-001`
- [ ] Switch to Org 2
- [ ] Search for `LC-ORG1-001`
- [ ] Verify it does NOT appear in results
- [ ] Try to access directly: `/bank/results?org=<org2_id>&q=LC-ORG1-001`
- [ ] Verify no results or error

### Expected Results
- ✅ Each org only sees its own data
- ✅ Org switcher correctly filters data
- ✅ API calls include correct org parameter
- ✅ Cross-org data is not accessible
- ✅ Saved views are org-scoped
- ✅ Exports are org-scoped

### Issues Found
- Issue 1: `________________`
- Issue 2: `________________`
- Issue 3: `________________`

### Test Result: [ ] PASS [ ] FAIL [ ] PARTIAL

---

## Test 2: Critical Flow Smoke Test

### Prerequisites
- Bank user logged in
- At least 10 validation sessions in database
- Org selected (or "All Organizations")

### Test Steps

#### Test 2.1: Results Filtering & Export
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=results`
- [ ] Verify results table loads
- [ ] Apply filter: Status = "Completed"
- [ ] Verify filtered results shown
- [ ] Apply filter: Client Name = "<specific_client>"
- [ ] Verify filtered results shown
- [ ] Clear filters
- [ ] Verify all results shown
- [ ] Click "Export CSV"
- [ ] Verify export job created (if > 10k rows) or download starts immediately
- [ ] If async job, verify job status updates
- [ ] Download CSV and verify data matches table
- [ ] Click "Export PDF"
- [ ] Verify PDF download works

#### Test 2.2: Duplicate Detection & Merge
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=results`
- [ ] Open a session detail modal (click on a result row)
- [ ] Check if duplicate badge appears
- [ ] Click "View Duplicates" if duplicates exist
- [ ] Verify duplicate candidates panel opens
- [ ] Verify similarity scores shown
- [ ] Click "Merge" on a candidate
- [ ] Verify merge modal opens
- [ ] Review merge preview
- [ ] Click "Confirm Merge"
- [ ] Verify merge completes successfully
- [ ] Verify merge history updated
- [ ] Verify original session updated with merged data

#### Test 2.3: Org Switching
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=results`
- [ ] Note current URL: `________________`
- [ ] Note number of results: `____`
- [ ] Open org switcher in sidebar
- [ ] Select a different org
- [ ] Verify URL updates with `?org=<new_org_id>`
- [ ] Verify results table refreshes
- [ ] Verify different results shown
- [ ] Switch back to original org
- [ ] Verify original results restored
- [ ] Select "All Organizations"
- [ ] Verify URL removes `org` parameter
- [ ] Verify all results shown

#### Test 2.4: API Token Management
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=integrations`
- [ ] Click "API Tokens" tab
- [ ] Click "Create Token"
- [ ] Fill in name: "Test Token"
- [ ] Select scopes: `read:results`, `read:approvals`
- [ ] Set expiration (optional)
- [ ] Click "Create"
- [ ] Verify token shown ONCE with warning
- [ ] Copy token: `________________`
- [ ] Close modal
- [ ] Verify token appears in list (masked)
- [ ] Click "Revoke" on test token
- [ ] Confirm revocation
- [ ] Verify token removed from list
- [ ] Test token with API call (should fail with 401)

#### Test 2.5: Webhook Management
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=integrations`
- [ ] Click "Webhooks" tab
- [ ] Click "Create Webhook"
- [ ] Fill in name: "Test Webhook"
- [ ] URL: `https://webhook.site/<unique_id>`
- [ ] Select events: `validation.completed`, `approval.created`
- [ ] Click "Create"
- [ ] Verify secret shown ONCE
- [ ] Copy secret: `________________`
- [ ] Close modal
- [ ] Verify webhook appears in list
- [ ] Click "Test" button
- [ ] Verify test delivery sent
- [ ] Check webhook.site for received payload
- [ ] Verify signature header present
- [ ] Click "View Logs"
- [ ] Verify delivery logs shown
- [ ] Click "Replay" on a failed delivery
- [ ] Verify replay sent
- [ ] Click "Rotate Secret"
- [ ] Verify new secret shown
- [ ] Delete test webhook
- [ ] Verify webhook removed

#### Test 2.6: Saved Views
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=results`
- [ ] Apply filters: Status="Completed", Client="<client>"
- [ ] Click "Save View"
- [ ] Name: "Test View"
- [ ] Click "Save"
- [ ] Verify view appears in saved views dropdown
- [ ] Clear filters
- [ ] Select "Test View" from dropdown
- [ ] Verify filters restored
- [ ] Verify results match saved filters
- [ ] Click "Share" on saved view
- [ ] Verify share option works (if implemented)
- [ ] Delete saved view
- [ ] Verify view removed

#### Test 2.7: AI Assistance with Quota
- [ ] Navigate to `/lcopilot/bank-dashboard?tab=results`
- [ ] Open a session with discrepancies
- [ ] Click "AI Assistance" tab
- [ ] Select a discrepancy
- [ ] Click "Explain Discrepancy"
- [ ] Verify explanation generated
- [ ] Verify quota remaining shown
- [ ] Note quota remaining: `____`
- [ ] Generate multiple explanations (if quota allows)
- [ ] When quota exhausted, verify friendly error message
- [ ] Verify error shows remaining quota: `0`
- [ ] Test "Generate Letter" (approval)
- [ ] Verify letter generated
- [ ] Test "Summarize Document"
- [ ] Verify summary generated
- [ ] Test "Translate Text"
- [ ] Verify translation generated

### Expected Results
- ✅ All critical flows work end-to-end
- ✅ Error states are user-friendly
- ✅ Loading states shown during async operations
- ✅ Quota enforcement works correctly
- ✅ Data persists correctly (saved views, tokens, webhooks)

### Issues Found
- Issue 1: `________________`
- Issue 2: `________________`
- Issue 3: `________________`

### Test Result: [ ] PASS [ ] FAIL [ ] PARTIAL

---

## Test 3: Browser Compatibility Check

### Prerequisites
- Same test data as Test 1 & 2
- Access to Chrome, Edge, Firefox browsers

### Test Steps

#### Test 3.1: Chrome (Latest)
- [ ] Open Chrome browser
- [ ] Navigate to `/lcopilot/bank-dashboard/login`
- [ ] Login with bank credentials
- [ ] Verify dashboard loads
- [ ] Test org switcher - verify dropdown works
- [ ] Test language switcher - verify dropdown works
- [ ] Navigate through all tabs:
  - [ ] Dashboard
  - [ ] Upload LC
  - [ ] Processing Queue
  - [ ] Results
  - [ ] Clients
  - [ ] Approvals
  - [ ] Discrepancies
  - [ ] Evidence Packs
  - [ ] Bulk Jobs
  - [ ] Integrations
- [ ] Test keyboard navigation (Tab key)
- [ ] Test filters on Results page
- [ ] Test export CSV/PDF
- [ ] Test duplicate merge flow
- [ ] Test AI assistance
- [ ] Check browser console for errors
- [ ] Verify no JavaScript errors

**Chrome Issues:**
- Issue 1: `________________`
- Issue 2: `________________`

#### Test 3.2: Microsoft Edge (Latest)
- [ ] Open Edge browser
- [ ] Navigate to `/lcopilot/bank-dashboard/login`
- [ ] Login with bank credentials
- [ ] Verify dashboard loads
- [ ] Test org switcher - verify dropdown works
- [ ] Test language switcher - verify dropdown works
- [ ] Navigate through all tabs (same as Chrome)
- [ ] Test keyboard navigation
- [ ] Test filters and exports
- [ ] Test duplicate merge flow
- [ ] Test AI assistance
- [ ] Check browser console for errors
- [ ] Verify no JavaScript errors

**Edge Issues:**
- Issue 1: `________________`
- Issue 2: `________________`

#### Test 3.3: Firefox (Latest)
- [ ] Open Firefox browser
- [ ] Navigate to `/lcopilot/bank-dashboard/login`
- [ ] Login with bank credentials
- [ ] Verify dashboard loads
- [ ] Test org switcher - verify dropdown works
- [ ] Test language switcher - verify dropdown works
- [ ] Navigate through all tabs (same as Chrome)
- [ ] Test keyboard navigation
- [ ] Test filters and exports
- [ ] Test duplicate merge flow
- [ ] Test AI assistance
- [ ] Check browser console for errors
- [ ] Verify no JavaScript errors

**Firefox Issues:**
- Issue 1: `________________`
- Issue 2: `________________`

#### Test 3.4: Mobile Responsiveness (Optional)
- [ ] Open Chrome DevTools → Toggle device toolbar
- [ ] Test on iPhone 12 Pro (375x812)
- [ ] Test on iPad (768x1024)
- [ ] Verify sidebar collapses on mobile
- [ ] Verify tables are scrollable
- [ ] Verify modals are full-screen on mobile
- [ ] Verify buttons are tappable

**Mobile Issues:**
- Issue 1: `________________`
- Issue 2: `________________`

### Expected Results
- ✅ All browsers render correctly
- ✅ No JavaScript errors in console
- ✅ All interactions work (dropdowns, modals, forms)
- ✅ Keyboard navigation works
- ✅ Responsive design works on mobile

### Issues Found
- Issue 1: `________________`
- Issue 2: `________________`
- Issue 3: `________________`

### Test Result: [ ] PASS [ ] FAIL [ ] PARTIAL

---

## Overall Test Summary

**Test 1 - Org Isolation**: [ ] PASS [ ] FAIL [ ] PARTIAL
**Test 2 - Critical Flows**: [ ] PASS [ ] FAIL [ ] PARTIAL
**Test 3 - Browser Compatibility**: [ ] PASS [ ] FAIL [ ] PARTIAL

**Overall Result**: [ ] READY TO LAUNCH [ ] NEEDS FIXES [ ] BLOCKED

**Blocking Issues:**
1. `________________`
2. `________________`
3. `________________`

**Non-Blocking Issues (can fix post-launch):**
1. `________________`
2. `________________`
3. `________________`

**Tester**: `________________`
**Date**: `________________`
**Environment**: [ ] Staging [ ] Production

