# Bank Dashboard Launch Tests - Execution Guide

## Prerequisites

Before running tests, ensure:
- [ ] Application is running (staging or production)
- [ ] Database access available
- [ ] At least 2 bank users exist
- [ ] Python 3.8+ installed (for setup scripts)
- [ ] Access to Chrome, Edge, and Firefox browsers

---

## Test 1: Org Isolation Test

### Step 1: Set Up Test Data

**Option A: Using Setup Script (Recommended)**
```bash
cd apps/api
python scripts/setup_org_isolation_test.py
```

The script will:
- Create 2 test organizations (APAC and EMEA)
- Assign users to organizations
- Tag existing validation sessions with org_ids

**Option B: Manual Setup**
1. Create 2 organizations via admin panel or SQL
2. Assign users to organizations
3. Tag validation sessions with org_ids in `extracted_data.bank_metadata.org_id`

### Step 2: Get Test Configuration

After running the setup script, note:
- Org 1 ID: `________________`
- Org 2 ID: `________________`
- User 1 Email/ID: `________________`
- User 2 Email/ID: `________________`

### Step 3: Verify API-Level Isolation (Optional)

```bash
# Get auth tokens for both users first
# Then run:
python apps/api/scripts/verify_org_isolation.py <org1_id> <org2_id> <user1_token> <user2_token>
```

This will verify that API endpoints correctly filter by org.

### Step 4: Execute Manual UI Tests

Follow the test steps in `docs/BANK_LAUNCH_TESTS.md` under "Test 1: Org Isolation Test".

**Key checks:**
1. Login as User 1 → Select Org 1 → Verify only Org 1 data visible
2. Switch to Org 2 → Verify different data shown
3. Verify Org 1 data NOT visible when Org 2 selected
4. Test on all pages: Results, Approvals, Discrepancies, Evidence Packs, Queue
5. Test exports are org-scoped
6. Test saved views are org-scoped

**Expected Result:** Each org only sees its own data, no cross-org leakage.

**Time Estimate:** 30-45 minutes

---

## Test 2: Critical Flow Smoke Test

### Step 1: Prepare Test Environment

- [ ] Login as bank user
- [ ] Ensure at least 10 validation sessions exist
- [ ] Select an org (or "All Organizations")

### Step 2: Execute Test Flows

Follow the test steps in `docs/BANK_LAUNCH_TESTS.md` under "Test 2: Critical Flow Smoke Test".

**Test each flow:**
1. **Results Filtering & Export** (5 min)
   - Apply filters
   - Export CSV/PDF
   - Verify exports match table data

2. **Duplicate Detection & Merge** (10 min)
   - Open session detail
   - View duplicates
   - Perform merge
   - Verify merge history

3. **Org Switching** (5 min)
   - Switch between orgs
   - Verify URL updates
   - Verify data refreshes

4. **API Token Management** (10 min)
   - Create token
   - Verify token shown once
   - Revoke token
   - Test API call fails

5. **Webhook Management** (15 min)
   - Create webhook
   - Test delivery
   - View logs
   - Replay failed delivery
   - Rotate secret

6. **Saved Views** (5 min)
   - Create saved view
   - Apply saved view
   - Verify filters restored

7. **AI Assistance** (10 min)
   - Test all AI features
   - Verify quota enforcement
   - Verify friendly error messages

**Expected Result:** All critical flows work end-to-end without errors.

**Time Estimate:** 60-90 minutes

---

## Test 3: Browser Compatibility Check

### Step 1: Prepare Test Environment

- [ ] Same test data as Test 1 & 2
- [ ] Chrome browser (latest)
- [ ] Microsoft Edge browser (latest)
- [ ] Firefox browser (latest)

### Step 2: Execute Browser Tests

Follow the test steps in `docs/BANK_LAUNCH_TESTS.md` under "Test 3: Browser Compatibility Check".

**For each browser:**
1. Login and verify dashboard loads
2. Test org switcher dropdown
3. Test language switcher dropdown
4. Navigate through all tabs
5. Test keyboard navigation (Tab key)
6. Test filters and exports
7. Test duplicate merge flow
8. Test AI assistance
9. Check browser console for errors

**Expected Result:** All browsers render correctly, no JavaScript errors.

**Time Estimate:** 45-60 minutes per browser (2-3 hours total)

---

## Test Execution Checklist

### Before Starting
- [ ] Read `docs/BANK_LAUNCH_TESTS.md` completely
- [ ] Set up test data (Test 1 Step 1)
- [ ] Have test credentials ready
- [ ] Have browser DevTools ready

### During Testing
- [ ] Document all issues found
- [ ] Take screenshots of errors
- [ ] Note browser console errors
- [ ] Record test results in checklist

### After Testing
- [ ] Review all issues found
- [ ] Categorize: Blocking vs Non-Blocking
- [ ] Create GitHub issues for blocking bugs
- [ ] Update test results in `docs/BANK_LAUNCH_TESTS.md`

---

## Quick Test Script (All Tests in One Session)

If you want to run all tests in one go:

1. **Setup** (10 min)
   ```bash
   python apps/api/scripts/setup_org_isolation_test.py
   python apps/api/scripts/verify_org_isolation.py <org1_id> <org2_id> <user1_token> <user2_token>
   ```

2. **Test 1: Org Isolation** (30 min)
   - Follow Test 1 steps

3. **Test 2: Critical Flows** (60 min)
   - Follow Test 2 steps

4. **Test 3: Browser Compatibility** (45 min per browser)
   - Chrome: 45 min
   - Edge: 45 min
   - Firefox: 45 min

**Total Time:** ~4-5 hours

---

## Troubleshooting

### Issue: Setup script fails
- Check database connection
- Verify bank company exists
- Check user emails match

### Issue: Org isolation not working
- Verify `org_id` is in `extracted_data.bank_metadata.org_id`
- Check `OrgScopeMiddleware` is registered
- Verify API client appends `org` param
- Check backend logs for org filtering

### Issue: Browser errors
- Check browser console for JavaScript errors
- Verify API calls are successful (Network tab)
- Check CORS headers if API calls fail
- Verify authentication tokens are valid

### Issue: Tests taking too long
- Focus on critical flows first
- Skip non-critical features
- Test one browser thoroughly, quick check on others

---

## Test Results Template

After completing tests, fill out:

```markdown
## Test Results - [Date]

### Test 1: Org Isolation
- Result: [ ] PASS [ ] FAIL [ ] PARTIAL
- Issues: 
  1. 
  2. 

### Test 2: Critical Flows
- Result: [ ] PASS [ ] FAIL [ ] PARTIAL
- Issues:
  1. 
  2. 

### Test 3: Browser Compatibility
- Chrome: [ ] PASS [ ] FAIL
- Edge: [ ] PASS [ ] FAIL
- Firefox: [ ] PASS [ ] FAIL
- Issues:
  1. 
  2. 

### Overall: [ ] READY TO LAUNCH [ ] NEEDS FIXES [ ] BLOCKED

### Blocking Issues:
1. 
2. 

### Non-Blocking Issues:
1. 
2. 
```

---

## Next Steps After Testing

1. **If all tests pass:**
   - Proceed with launch
   - Monitor closely for first 24 hours
   - Have rollback plan ready

2. **If blocking issues found:**
   - Fix issues
   - Re-run affected tests
   - Re-evaluate launch readiness

3. **If non-blocking issues found:**
   - Document issues
   - Plan fixes for post-launch
   - Proceed with launch if critical flows work

