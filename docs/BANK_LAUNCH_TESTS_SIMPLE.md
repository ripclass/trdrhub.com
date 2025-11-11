# Bank Dashboard Launch Tests - PRACTICAL VERSION

## Important Note

**If you don't have multiple organizations set up**, that's OK! The org feature is optional. You can:
- Test with "All Organizations" selected (default)
- Skip org isolation tests if you're a single-branch bank
- The system works fine without orgs - they're just for multi-branch banks

---

## Test 1: Org Isolation Test (OPTIONAL)

### Do You Need This Test?

**Skip this test if:**
- You're a single-branch bank
- You don't have multiple regions/branches
- You see "All Organizations" in the dropdown and that's fine

**Run this test if:**
- You're a multi-branch/multi-region bank
- You need to separate data by branch/region
- You've already created orgs in the system

### If You Have No Orgs Yet

**Option 1: Test Without Orgs (Recommended for Launch)**
- Just verify "All Organizations" works
- Verify data loads correctly
- Skip org isolation tests

**Option 2: Create Test Orgs (If Needed)**
You can create orgs via API or wait for admin UI. For now, the system works fine with "All Organizations".

### Simplified Test (No Orgs Required)

1. **Login to Bank Dashboard**
   - [ ] Login as bank user
   - [ ] Navigate to `/lcopilot/bank-dashboard`

2. **Check Org Switcher**
   - [ ] See "All Organizations" in dropdown (or empty list)
   - [ ] Dropdown opens/closes correctly
   - [ ] No errors in browser console

3. **Verify Data Loads**
   - [ ] Navigate to Results tab
   - [ ] Data loads correctly
   - [ ] Filters work
   - [ ] No errors

**That's it!** If org switcher shows "All Organizations" and data loads, you're good.

---

## Test 2: Critical Flow Smoke Test

### Prerequisites
- Bank user logged in
- At least some validation sessions exist (or use mock data)

### Simplified Test Steps

#### 1. Results Page (5 min)
- [ ] Navigate to Results tab
- [ ] Table loads (even if empty)
- [ ] Try a filter (status, client name)
- [ ] Try search box
- [ ] Click Export CSV (should work or show friendly message)

#### 2. Duplicate Detection (5 min)
- [ ] Open a result detail modal
- [ ] Check if "View Duplicates" button appears
- [ ] If duplicates exist, verify they show
- [ ] If no duplicates, verify friendly message

#### 3. Org Switching (2 min)
- [ ] Click org switcher dropdown
- [ ] See "All Organizations" option
- [ ] Select it (should work)
- [ ] Verify URL updates (or stays same if already selected)

#### 4. API Tokens (5 min)
- [ ] Navigate to Integrations tab → API Tokens
- [ ] Click "Create Token"
- [ ] Fill form and create
- [ ] Verify token shown once
- [ ] Verify token appears in list (masked)

#### 5. Webhooks (5 min)
- [ ] Navigate to Integrations tab → Webhooks
- [ ] Click "Create Webhook"
- [ ] Fill form and create
- [ ] Verify webhook appears in list

#### 6. Saved Views (5 min)
- [ ] On Results page, apply some filters
- [ ] Click "Save View"
- [ ] Name it and save
- [ ] Verify it appears in saved views dropdown
- [ ] Select it and verify filters restore

#### 7. AI Assistance (5 min)
- [ ] Open a result with discrepancies
- [ ] Click "AI Assistance" tab
- [ ] Try "Explain Discrepancy"
- [ ] Verify explanation appears
- [ ] Check quota remaining shown

**Total Time: ~30 minutes**

---

## Test 3: Browser Compatibility Check

### Quick Test (15 min per browser)

**For each browser (Chrome, Edge, Firefox):**

1. **Login & Navigation** (2 min)
   - [ ] Login works
   - [ ] Dashboard loads
   - [ ] Navigate between tabs (no errors)

2. **Key Interactions** (5 min)
   - [ ] Click org switcher (works)
   - [ ] Click language switcher (works)
   - [ ] Apply filters on Results page
   - [ ] Open a modal/dialog
   - [ ] Close modal

3. **Check Console** (2 min)
   - [ ] Open browser DevTools (F12)
   - [ ] Check Console tab
   - [ ] Verify no red errors (warnings OK)

4. **Basic Functionality** (5 min)
   - [ ] Create a saved view
   - [ ] Export CSV (or verify button works)
   - [ ] Use AI assistance
   - [ ] Navigate back/forward

**That's it!** If everything works and no errors, browser compatibility is good.

**Total Time: ~45 minutes (15 min × 3 browsers)**

---

## What If Something Doesn't Work?

### Common Issues

1. **"No organizations found"**
   - ✅ This is OK! Just use "All Organizations"
   - Org feature is optional

2. **Empty data tables**
   - ✅ This is OK if you have no validation sessions
   - Verify the UI loads (empty state shows)

3. **API errors**
   - Check browser console for details
   - Verify backend is running
   - Check network tab for failed requests

4. **Org switcher shows nothing**
   - ✅ This is OK! Means no orgs created yet
   - System works fine with "All Organizations"

---

## Quick Launch Checklist

**Minimum Required Tests:**

- [ ] Login works
- [ ] Dashboard loads
- [ ] Can navigate between tabs
- [ ] Results page loads (even if empty)
- [ ] Filters work
- [ ] No JavaScript errors in console
- [ ] Works in Chrome (your primary browser)

**Nice to Have:**

- [ ] Works in Edge/Firefox
- [ ] Org switcher works (if you have orgs)
- [ ] All critical flows tested

---

## Summary

**You DON'T need orgs to launch!** The org feature is:
- Optional (for multi-branch banks)
- Works fine with "All Organizations"
- Can be set up later when needed

**Focus on:**
1. Basic functionality works
2. No errors
3. Critical flows work
4. Browser compatibility (at least Chrome)

The automated tests already verified the code is correct. Manual tests just verify the UI works!

