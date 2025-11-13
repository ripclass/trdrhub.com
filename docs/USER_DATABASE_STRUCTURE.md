# User Database Structure

## Overview

User data is stored in **two places**:

1. **Supabase Auth** (`auth.users` table) - Authentication credentials
2. **Backend PostgreSQL** (`users` and `companies` tables) - User profile and company data

## Database Tables

### 1. Supabase Auth (`auth.users`)

**Purpose**: Authentication only - stores email/password credentials

**Fields**:
- `id` (UUID) - User ID
- `email` - User email address
- `encrypted_password` - Hashed password
- `user_metadata` (JSONB) - Optional metadata like `full_name`, `role`
- `created_at`, `updated_at` - Timestamps

**Note**: This is managed by Supabase. We don't directly query this table.

---

### 2. Backend PostgreSQL: `users` Table

**Purpose**: User profile, role, and onboarding data

**Key Fields**:
```sql
- id (UUID) - Primary key
- email (String) - Unique, indexed
- hashed_password (String) - For backend authentication
- full_name (String) - Contact person name
- role (String) - User role: exporter, importer, tenant_admin, bank_officer, bank_admin, system_admin
- company_id (UUID) - Foreign key to companies table
- is_active (Boolean) - Account status
- onboarding_completed (Boolean) - Onboarding status
- onboarding_data (JSONB) - Stores:
  - business_types: ["exporter", "importer"]
  - company: { name, type, size }
  - contact_person: "Full Name"
- onboarding_step (String) - Current onboarding step
- status (String) - Approval status (active, pending, approved, etc.)
- kyc_required (Boolean) - For bank users
- kyc_status (String) - KYC processing status
- created_at, updated_at, deleted_at - Timestamps
```

**Role Values**:
- `exporter` - SME Exporter (1-20 employees)
- `importer` - SME Importer (1-20 employees)
- `tenant_admin` - Medium/Large Enterprise (21+ employees, both exporter & importer)
- `bank_officer` - Bank user
- `bank_admin` - Bank administrator
- `system_admin` - System administrator

---

### 3. Backend PostgreSQL: `companies` Table

**Purpose**: Company/organization information

**Key Fields**:
```sql
- id (UUID) - Primary key
- name (String) - Company name
- contact_email (String) - Primary contact email
- legal_name (String) - Legal entity name (for banks)
- registration_number (String) - Business registration number
- regulator_id (String) - Regulatory ID (for banks)
- country (String) - Country of operation
- event_metadata (JSONB) - Stores:
  - business_type: "exporter" | "importer" | "both" | "bank"
  - company_size: "sme" | "medium" | "large"
- plan (Enum) - Billing plan (free, pay_per_check, monthly_basic, etc.)
- status (Enum) - Company status (active, trial, suspended, etc.)
- created_at, updated_at - Timestamps
```

**Relationship**: 
- One Company can have many Users (`users.company_id` → `companies.id`)
- Each User belongs to one Company (or null for system admins)

---

## User Registration Flow

### Step 1: User Fills Registration Form

User provides:
- Email
- Password
- Company name
- Contact person (full name)
- Company type (exporter, importer, both, bank)
- Company size (if "both" type: sme, medium, large)

### Step 2: Frontend Calls `registerWithEmail()`

**Supabase Auth**:
- Creates user in `auth.users` table
- Stores email and hashed password
- Stores `full_name` and `role` in `user_metadata`

**Backend API** (`/auth/register`):
- Creates user in `users` table with:
  - Email, password hash, full_name, role
  - **Creates Company record** if `company_name` provided:
    - Company name, contact email
    - Company type and size in `event_metadata`
  - Links user to company via `company_id`
  - Stores company info in `onboarding_data` JSONB:
    ```json
    {
      "business_types": ["exporter", "importer"],
      "company": {
        "name": "ABC Export Ltd",
        "type": "both",
        "size": "sme"
      },
      "contact_person": "John Doe"
    }
    ```

### Step 3: Data Storage Summary

**Supabase Auth** (`auth.users`):
- ✅ Email
- ✅ Password (hashed)
- ✅ Full name (in metadata)
- ✅ Role (in metadata)

**Backend PostgreSQL** (`users` table):
- ✅ Email
- ✅ Password hash (for backend auth)
- ✅ Full name (contact person)
- ✅ Role (exporter, importer, tenant_admin, bank_officer, etc.)
- ✅ Company ID (link to company)
- ✅ Onboarding data (JSONB with company info, business types)

**Backend PostgreSQL** (`companies` table):
- ✅ Company name
- ✅ Contact email
- ✅ Company type (in `event_metadata.business_type`)
- ✅ Company size (in `event_metadata.company_size`)

---

## Example User Records

### User 1: SME Exporter

**Supabase Auth**:
```json
{
  "id": "uuid-1",
  "email": "john@exportco.com",
  "user_metadata": {
    "full_name": "John Doe",
    "role": "exporter"
  }
}
```

**Backend `users` table**:
```json
{
  "id": "uuid-1",
  "email": "john@exportco.com",
  "full_name": "John Doe",
  "role": "exporter",
  "company_id": "company-uuid-1",
  "onboarding_data": {
    "business_types": ["exporter"],
    "company": {
      "name": "ABC Export Co",
      "type": "exporter",
      "size": null
    },
    "contact_person": "John Doe"
  }
}
```

**Backend `companies` table**:
```json
{
  "id": "company-uuid-1",
  "name": "ABC Export Co",
  "contact_email": "john@exportco.com",
  "event_metadata": {
    "business_type": "exporter"
  }
}
```

### User 2: Medium Enterprise (Both Exporter & Importer)

**Backend `users` table**:
```json
{
  "id": "uuid-2",
  "email": "admin@bigcorp.com",
  "full_name": "Jane Smith",
  "role": "tenant_admin",
  "company_id": "company-uuid-2",
  "onboarding_data": {
    "business_types": ["exporter", "importer"],
    "company": {
      "name": "Big Corp International",
      "type": "both",
      "size": "medium"
    },
    "contact_person": "Jane Smith"
  }
}
```

**Backend `companies` table**:
```json
{
  "id": "company-uuid-2",
  "name": "Big Corp International",
  "contact_email": "admin@bigcorp.com",
  "event_metadata": {
    "business_type": "both",
    "company_size": "medium"
  }
}
```

### User 3: Bank Officer

**Backend `users` table**:
```json
{
  "id": "uuid-3",
  "email": "officer@bank.com",
  "full_name": "Bob Banker",
  "role": "bank_officer",
  "company_id": "company-uuid-3",
  "kyc_required": true,
  "kyc_status": "pending",
  "status": "pending",
  "onboarding_data": {
    "business_types": ["bank"],
    "company": {
      "name": "Global Bank",
      "type": "bank"
    }
  }
}
```

---

## Querying User Data

### Get User with Company Info

```python
user = db.query(User).filter(User.email == email).first()
company = user.company  # Relationship access
company_type = company.event_metadata.get("business_type")
company_size = company.event_metadata.get("company_size")
```

### Get User Role and Business Types

```python
user = db.query(User).filter(User.email == email).first()
role = user.role  # "exporter", "importer", "tenant_admin", etc.
business_types = user.onboarding_data.get("business_types", [])
```

### Get All Users by Company Type

```python
# Get all SME exporters
users = db.query(User).join(Company).filter(
    Company.event_metadata["business_type"].astext == "exporter",
    User.role == "exporter"
).all()
```

---

## Important Notes

1. **Company info is saved during registration** - No need to wait for onboarding wizard
2. **User role determines dashboard** - Set during registration based on company type/size
3. **Company size only matters for "both" type** - Determines if user gets `tenant_admin` role
4. **Onboarding data is JSONB** - Flexible storage for additional info collected later
5. **Company metadata is in `event_metadata`** - Stores business_type and company_size
6. **Contact person = full_name** - The person registering is the contact person

---

## Migration Notes

If you have existing users without company records:

1. Run a migration to create Company records for users with `company_id = NULL`
2. Extract company info from `onboarding_data` if available
3. Set `company_id` on users to link them to their company

