# How to Create Bank Organizations & Test Data

## Current Status: No UI Yet! 

**Right now, orgs are created via API only.** A UI will be added later. For testing, you can:

1. **Use the Python script** (easiest)
2. **Use API directly** (curl/Postman)
3. **Use SQL directly** (advanced)

---

## Method 1: Use Python Script (EASIEST - Recommended)

### Step 1: Run the Setup Script

```bash
cd apps/api
python scripts/setup_org_isolation_test.py
```

**What it does:**
- Creates 2 test orgs (APAC, EMEA)
- Tags existing validation sessions with org IDs
- Assigns users to orgs (if they exist)

**Note:** The script will ask for user IDs if test users don't exist. You can skip user assignment if you just want to test org filtering.

### Step 2: Check What Was Created

After running the script, it will print:
- Org 1 ID and Name
- Org 2 ID and Name
- How many sessions were tagged

**Save these IDs!** You'll need them for testing.

---

## Method 2: Create Orgs via API (Using Browser/Postman)

### Step 1: Get Your Bank Company ID

1. Login to Bank Dashboard
2. Open browser DevTools (F12)
3. Go to Network tab
4. Make any API call (e.g., navigate to Results page)
5. Find a request to `/bank/results` or similar
6. Look at the response - it should include your `company_id`

**OR** check your database:
```sql
SELECT id, name FROM companies WHERE company_type = 'bank';
```

### Step 2: Get Your Auth Token

1. In browser DevTools → Network tab
2. Find any `/bank/*` request
3. Look at Request Headers
4. Copy the `Authorization` header value (e.g., `Bearer eyJ...`)

### Step 3: Create Org 1 (APAC)

**Using Browser Console:**

```javascript
// Replace YOUR_TOKEN and YOUR_COMPANY_ID
const token = "Bearer YOUR_TOKEN_HERE";
const companyId = "YOUR_COMPANY_ID_HERE";

fetch("http://localhost:8000/bank/orgs", {
  method: "POST",
  headers: {
    "Authorization": token,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    bank_company_id: companyId,
    kind: "region",
    name: "Test Bank - APAC",
    code: "APAC",
    level: 0,
    sort_order: 1,
    is_active: true
  })
})
.then(r => r.json())
.then(data => {
  console.log("Org 1 created:", data);
  console.log("Org 1 ID:", data.id);
});
```

**Using curl:**

```bash
curl -X POST "http://localhost:8000/bank/orgs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_company_id": "YOUR_COMPANY_ID",
    "kind": "region",
    "name": "Test Bank - APAC",
    "code": "APAC",
    "level": 0,
    "sort_order": 1,
    "is_active": true
  }'
```

### Step 4: Create Org 2 (EMEA)

Same as Step 3, but change:
- `name`: "Test Bank - EMEA"
- `code`: "EMEA"
- `sort_order`: 2

**Save both org IDs!**

---

## Method 3: Create Test Data Manually (SQL)

### Step 1: Find Your Bank Company ID

```sql
SELECT id, name FROM companies WHERE company_type = 'bank';
```

### Step 2: Create Org 1

```sql
INSERT INTO bank_orgs (
    id, 
    bank_company_id, 
    parent_id, 
    kind, 
    name, 
    code, 
    path, 
    level, 
    sort_order, 
    is_active,
    created_at,
    updated_at
)
VALUES (
    gen_random_uuid(),  -- Will generate a UUID
    '<YOUR_BANK_COMPANY_ID>',  -- Replace this!
    NULL,
    'region',
    'Test Bank - APAC',
    'APAC',
    '/temp',  -- Will be updated after insert
    0,
    1,
    true,
    NOW(),
    NOW()
)
RETURNING id;
```

**Save the returned ID!** Let's call it `ORG1_ID`.

### Step 3: Update Org 1 Path

```sql
UPDATE bank_orgs 
SET path = '/' || id::text 
WHERE name = 'Test Bank - APAC';
```

### Step 4: Create Org 2

```sql
INSERT INTO bank_orgs (
    id, 
    bank_company_id, 
    parent_id, 
    kind, 
    name, 
    code, 
    path, 
    level, 
    sort_order, 
    is_active,
    created_at,
    updated_at
)
VALUES (
    gen_random_uuid(),
    '<YOUR_BANK_COMPANY_ID>',  -- Replace this!
    NULL,
    'region',
    'Test Bank - EMEA',
    'EMEA',
    '/temp',
    0,
    2,
    true,
    NOW(),
    NOW()
)
RETURNING id;
```

**Save the returned ID!** Let's call it `ORG2_ID`.

### Step 5: Update Org 2 Path

```sql
UPDATE bank_orgs 
SET path = '/' || id::text 
WHERE name = 'Test Bank - EMEA';
```

### Step 6: Tag Existing Sessions with Org IDs

**Tag some sessions as Org 1:**

```sql
UPDATE validation_sessions 
SET extracted_data = jsonb_set(
    COALESCE(extracted_data, '{}'::jsonb),
    '{bank_metadata,org_id}',
    to_jsonb('<ORG1_ID>'::text)
)
WHERE company_id = '<YOUR_BANK_COMPANY_ID>'
  AND deleted_at IS NULL
  AND id IN (
    SELECT id FROM validation_sessions 
    WHERE company_id = '<YOUR_BANK_COMPANY_ID>'
      AND deleted_at IS NULL
    LIMIT 5  -- Tag first 5 sessions
  );
```

**Tag other sessions as Org 2:**

```sql
UPDATE validation_sessions 
SET extracted_data = jsonb_set(
    COALESCE(extracted_data, '{}'::jsonb),
    '{bank_metadata,org_id}',
    to_jsonb('<ORG2_ID>'::text)
)
WHERE company_id = '<YOUR_BANK_COMPANY_ID>'
  AND deleted_at IS NULL
  AND id IN (
    SELECT id FROM validation_sessions 
    WHERE company_id = '<YOUR_BANK_COMPANY_ID>'
      AND deleted_at IS NULL
      AND (extracted_data->'bank_metadata'->>'org_id') IS NULL  -- Only untagged ones
    LIMIT 5  -- Tag next 5 sessions
  );
```

### Step 7: Assign Users to Orgs (Optional)

**Find your user ID:**

```sql
SELECT id, email FROM users WHERE company_id = '<YOUR_BANK_COMPANY_ID>';
```

**Assign User 1 to Org 1:**

```sql
INSERT INTO user_org_access (user_id, org_id, role, created_at)
VALUES (
    '<USER1_ID>',  -- Replace with your user ID
    '<ORG1_ID>',  -- Replace with Org 1 ID
    'admin',
    NOW()
);
```

**Assign User 2 to Org 2 (or same user to both):**

```sql
INSERT INTO user_org_access (user_id, org_id, role, created_at)
VALUES (
    '<USER2_ID>',  -- Replace with your user ID
    '<ORG2_ID>',  -- Replace with Org 2 ID
    'admin',
    NOW()
);
```

---

## Verify Test Data Was Created

### Check Orgs Exist

```sql
SELECT id, name, code, kind FROM bank_orgs 
WHERE bank_company_id = '<YOUR_BANK_COMPANY_ID>';
```

Should show:
- Test Bank - APAC (APAC)
- Test Bank - EMEA (EMEA)

### Check Sessions Are Tagged

```sql
SELECT 
    id,
    (extracted_data->'bank_metadata'->>'org_id') as org_id,
    (extracted_data->'bank_metadata'->>'lc_number') as lc_number
FROM validation_sessions
WHERE company_id = '<YOUR_BANK_COMPANY_ID>'
  AND deleted_at IS NULL
  AND (extracted_data->'bank_metadata'->>'org_id') IS NOT NULL
LIMIT 10;
```

Should show sessions with `org_id` values.

### Check User Access

```sql
SELECT 
    u.email,
    bo.name as org_name,
    uoa.role
FROM user_org_access uoa
JOIN users u ON uoa.user_id = u.id
JOIN bank_orgs bo ON uoa.org_id = bo.id
WHERE u.company_id = '<YOUR_BANK_COMPANY_ID>';
```

---

## Test in UI

1. **Refresh Bank Dashboard**
   - Org switcher should now show "Test Bank - APAC" and "Test Bank - EMEA"

2. **Select Org 1**
   - Click org switcher
   - Select "Test Bank - APAC"
   - Results should filter to only show sessions tagged with Org 1

3. **Select Org 2**
   - Click org switcher
   - Select "Test Bank - EMEA"
   - Results should filter to only show sessions tagged with Org 2

4. **Select "All Organizations"**
   - Should show all sessions from both orgs

---

## Quick Reference: API Endpoints

### Create Org
```
POST /bank/orgs
Authorization: Bearer <token>
Content-Type: application/json

{
  "bank_company_id": "<uuid>",
  "kind": "region",  // or "branch" or "group"
  "name": "Org Name",
  "code": "ORG1",
  "level": 0,
  "sort_order": 1,
  "is_active": true
}
```

### List Orgs
```
GET /bank/orgs
Authorization: Bearer <token>
```

### Assign User to Org
```
POST /bank/orgs/access
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": "<uuid>",
  "org_id": "<uuid>",
  "role": "admin"  // or "member" or "viewer"
}
```

---

## Troubleshooting

**"No organizations found" in UI:**
- Check orgs were created: `SELECT * FROM bank_orgs WHERE bank_company_id = '<your_id>';`
- Check user has access: `SELECT * FROM user_org_access WHERE user_id = '<your_user_id>';`
- Refresh browser (orgs are cached)

**Sessions not filtering:**
- Check sessions have `org_id` in `extracted_data->bank_metadata->org_id`
- Verify org IDs match exactly (UUIDs are case-sensitive)

**Can't create org via API:**
- Verify you're logged in as `bank_admin` (not `bank_officer`)
- Check `bank_company_id` matches your company ID
- Check backend logs for errors

---

## Next Steps

Once test data is created:
1. Run manual UI tests (see `docs/BANK_LAUNCH_TESTS.md`)
2. Verify org isolation works
3. Test switching between orgs
4. Verify "All Organizations" shows everything

