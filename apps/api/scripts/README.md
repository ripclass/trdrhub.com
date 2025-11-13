# Database Verification Scripts

Scripts to verify that user registration data is stored correctly in the database.

## verify_user_data.py

Verifies all registration data for a user by email address.

### Usage

```bash
# From project root
cd apps/api
python scripts/verify_user_data.py <email>

# Example
python scripts/verify_user_data.py ripexpimp@gmail.com
```

### What it checks

1. ✅ User record exists in `users` table
2. ✅ Company record exists (by `company_id` or `contact_email`)
3. ✅ Company data is complete (`name`, `contact_email`, `event_metadata`)
4. ✅ `onboarding_data` JSONB contains:
   - `company` object (name, type, size)
   - `business_types` array
   - `contact_person` string

### Output

The script prints:
- User details (ID, email, name, role)
- Company linkage status
- Company data (if found)
- Onboarding data contents
- Issues found (if any)
- SQL recommendations to fix issues

### Example Output

```
============================================================
🔍 Verifying data for user: ripexpimp@gmail.com
============================================================

✅ User found:
   - ID: feacca06-2de4-4cef-b334-6bbbb13fffc1
   - Email: ripexpimp@gmail.com
   - Full Name: RC EXPnIMP
   - Role: exporter
   - Is Active: True
   - Created At: 2025-11-13 12:38:58.890533

📋 Company Linkage:
   ✅ company_id: abc123-def456-...

🏢 Company Data:
   - ID: abc123-def456-...
   - Name: Your Company Name
   - Contact Email: ripexpimp@gmail.com
   - Event Metadata:
      - business_type: both
      - company_size: sme

📦 Onboarding Data (users.onboarding_data JSONB):
   ✅ onboarding_data exists
   
   📋 Contents:
      ✅ company:
         - name: Your Company Name
         - type: both
         - size: sme
      ✅ business_types: ['exporter', 'importer']
      ✅ contact_person: RC EXPnIMP

============================================================
📊 SUMMARY
============================================================

✅ ALL DATA PRESENT AND CORRECT!
   - User has company_id: abc123-def456-...
   - Company record exists: Your Company Name
   - Onboarding data complete: Yes

============================================================
```

## Admin API Endpoint

You can also verify user data via the admin API endpoint:

### Endpoint

```
GET /admin/users/{user_id}/verify-data
```

### Authentication

Requires admin privileges (admin JWT token).

### Example Request

```bash
curl -X GET "https://trdrhub-api.onrender.com/admin/users/{user_id}/verify-data" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN"
```

### Response Format

```json
{
  "user_id": "feacca06-2de4-4cef-b334-6bbbb13fffc1",
  "email": "ripexpimp@gmail.com",
  "full_name": "RC EXPnIMP",
  "role": "exporter",
  "is_active": true,
  "created_at": "2025-11-13T12:38:58.890533",
  "checks": {
    "user_exists": true,
    "has_company_id": true,
    "company_exists": true,
    "company_found_by_id": true,
    "company_found_by_email": false,
    "has_onboarding_data": true,
    "onboarding_data_complete": true
  },
  "company": {
    "id": "abc123-def456-...",
    "name": "Your Company Name",
    "contact_email": "ripexpimp@gmail.com",
    "legal_name": null,
    "registration_number": null,
    "country": null,
    "regulator_id": null,
    "event_metadata": {
      "business_type": "both",
      "company_size": "sme"
    }
  },
  "onboarding_data": {
    "company": {
      "name": "Your Company Name",
      "type": "both",
      "size": "sme"
    },
    "business_types": ["exporter", "importer"],
    "contact_person": "RC EXPnIMP"
  },
  "issues": [],
  "recommendations": [],
  "status": "complete",
  "status_message": "All data present and correct"
}
```

## Troubleshooting

### User has no company_id

If `company_id` is NULL but a company exists with matching `contact_email`:

```sql
UPDATE users SET company_id = '<company_id>' WHERE id = '<user_id>';
```

### Company not found

If no company record exists, check:
1. Was registration completed successfully?
2. Did the backend `/auth/register` endpoint create the company?
3. Check backend logs for errors during registration

### Onboarding data missing

If `onboarding_data` is empty or incomplete:
1. Check if company data exists in `companies` table
2. The `/onboarding/status` endpoint should auto-restore data from company record
3. If not, manually restore:

```sql
UPDATE users 
SET onboarding_data = jsonb_build_object(
  'company', jsonb_build_object(
    'name', c.name,
    'type', c.event_metadata->>'business_type',
    'size', c.event_metadata->>'company_size'
  ),
  'business_types', CASE 
    WHEN c.event_metadata->>'business_type' = 'both' 
    THEN '["exporter", "importer"]'::jsonb
    ELSE jsonb_build_array(c.event_metadata->>'business_type')
  END,
  'contact_person', u.full_name
)
FROM companies c
WHERE u.company_id = c.id AND u.email = '<email>';
```

