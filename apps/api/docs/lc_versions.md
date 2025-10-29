# LC Version Control System

## Overview

The LC Version Control System provides complete version tracking for Letter of Credit (LC) amendments and revisions. This system automatically creates V1 when an LC is first validated and allows users to upload amendments as V2, V3, etc., with full comparison and history tracking.

## Architecture

### Database Schema

#### `lc_versions` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `lc_number` | VARCHAR(100) | LC number (indexed) |
| `version` | INTEGER | Version number (1, 2, 3, etc.) |
| `validation_session_id` | UUID | Foreign key to `validation_sessions.id` |
| `uploaded_by` | UUID | Foreign key to `users.id` |
| `created_at` | TIMESTAMP | Auto-generated timestamp |
| `status` | VARCHAR(20) | Enum: `draft`, `validated`, `packaged` |
| `file_metadata` | JSONB | File information and metadata |

#### Constraints

- **Unique Constraint**: `(lc_number, version)` - Ensures no duplicate versions per LC
- **Indexes**:
  - `lc_number` (for fast lookups)
  - `created_at` (for chronological queries)
  - `status` (for status filtering)

#### Relationships

- `validation_session_id` → `validation_sessions.id` (Many-to-One)
- `uploaded_by` → `users.id` (Many-to-One)

### File Metadata Structure

The `file_metadata` JSONB column stores:

```json
{
  "files": [
    {
      "name": "LC_Original.pdf",
      "size": 1024000,
      "type": "application/pdf",
      "document_type": "letter_of_credit",
      "s3_key": "lc/BD-2024-001/v1/LC_Original.pdf",
      "document_id": "uuid-here"
    }
  ],
  "total_files": 3,
  "total_size": 2048000,
  "uploaded_at": "2024-01-15T10:30:00Z"
}
```

## API Endpoints

### Base URL: `/lc`

All endpoints require JWT authentication.

### 1. Create LC Version

**POST** `/lc/{lc_number}/versions`

Creates a new version for an LC with auto-incremented version numbers.

#### Request Body

```json
{
  "validation_session_id": "uuid",
  "uploaded_by": "uuid",
  "file_metadata": {
    "files": [
      {
        "name": "document.pdf",
        "size": 1024000,
        "type": "application/pdf",
        "document_type": "letter_of_credit"
      }
    ]
  }
}
```

#### Response (201 Created)

```json
{
  "id": "uuid",
  "lc_number": "BD-2024-001",
  "version": 2,
  "validation_session_id": "uuid",
  "uploaded_by": "uuid",
  "created_at": "2024-01-15T10:30:00Z",
  "status": "draft",
  "file_metadata": {
    "files": [...],
    "total_files": 3,
    "total_size": 2048000
  }
}
```

#### cURL Example

```bash
curl -X POST "https://api.lcopilot.com/lc/BD-2024-001/versions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "validation_session_id": "12345678-1234-1234-1234-123456789012",
    "uploaded_by": "87654321-4321-4321-4321-210987654321",
    "file_metadata": {
      "files": [
        {
          "name": "LC_Amendment.pdf",
          "size": 1024000,
          "type": "application/pdf",
          "document_type": "letter_of_credit"
        }
      ]
    }
  }'
```

### 2. Get All Versions

**GET** `/lc/{lc_number}/versions`

Retrieves all versions for a specific LC number.

#### Response (200 OK)

```json
{
  "lc_number": "BD-2024-001",
  "versions": [
    {
      "id": "uuid",
      "lc_number": "BD-2024-001",
      "version": 1,
      "status": "validated",
      "created_at": "2024-01-10T09:00:00Z",
      "file_metadata": {...}
    },
    {
      "id": "uuid",
      "lc_number": "BD-2024-001",
      "version": 2,
      "status": "draft",
      "created_at": "2024-01-15T10:30:00Z",
      "file_metadata": {...}
    }
  ],
  "total_versions": 2,
  "latest_version": 2
}
```

#### cURL Example

```bash
curl -X GET "https://api.lcopilot.com/lc/BD-2024-001/versions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. Compare Versions

**GET** `/lc/{lc_number}/versions/compare?from=V1&to=V2`

Compares two versions and returns differences in discrepancies.

#### Query Parameters

- `from` (required): Source version (e.g., "V1")
- `to` (required): Target version (e.g., "V2")

#### Response (200 OK)

```json
{
  "lc_number": "BD-2024-001",
  "from_version": "V1",
  "to_version": "V2",
  "changes": {
    "added_discrepancies": [
      {
        "id": "disc-uuid",
        "title": "New Issue Found",
        "description": "Date mismatch in shipping documents",
        "severity": "medium",
        "rule_name": "UCP 600 Article 14"
      }
    ],
    "removed_discrepancies": [
      {
        "id": "disc-uuid",
        "title": "Amount Issue Resolved",
        "description": "Invoice amount corrected",
        "severity": "high",
        "rule_name": "UCP 600 Article 18"
      }
    ],
    "modified_discrepancies": [],
    "status_change": {
      "from": "draft",
      "to": "validated"
    }
  },
  "summary": {
    "total_changes": 2,
    "improvement_score": 0.5
  }
}
```

#### cURL Example

```bash
curl -X GET "https://api.lcopilot.com/lc/BD-2024-001/versions/compare?from=V1&to=V2" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. Check LC Existence

**GET** `/lc/{lc_number}/check`

Checks if an LC exists and returns version information.

#### Response (200 OK)

```json
{
  "exists": true,
  "next_version": "V3",
  "current_versions": 2,
  "latest_version_id": "uuid"
}
```

#### cURL Example

```bash
curl -X GET "https://api.lcopilot.com/lc/BD-2024-001/check" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. Get Amended LCs

**GET** `/lc/amended`

Returns all LCs that have multiple versions (amendments).

#### Response (200 OK)

```json
[
  {
    "lc_number": "BD-2024-001",
    "versions": 3,
    "latest_version": "V3",
    "last_updated": "2024-01-20T14:30:00Z"
  },
  {
    "lc_number": "BD-2024-002",
    "versions": 2,
    "latest_version": "V2",
    "last_updated": "2024-01-18T11:15:00Z"
  }
]
```

#### cURL Example

```bash
curl -X GET "https://api.lcopilot.com/lc/amended" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## CRUD Operations

### Using the LCVersionCRUD Class

```python
from app.crud.lc_versions import LCVersionCRUD
from app.database import get_db

# Create a new version
version = LCVersionCRUD.create_new_version(
    db=db,
    lc_number="BD-2024-001",
    user_id=user.id,
    validation_session_id=session.id,
    files=[{"name": "doc.pdf", "size": 1024}]
)

# Get all versions for an LC
versions = LCVersionCRUD.get_versions(db, "BD-2024-001")

# Compare versions
comparison = LCVersionCRUD.compare_versions(
    db=db,
    lc_number="BD-2024-001",
    from_version="V1",
    to_version="V2"
)

# Check if LC exists
exists_info = LCVersionCRUD.check_lc_exists(db, "BD-2024-001")
```

## Version Seeding

### Automatic V1 Creation

The system automatically creates V1 when a validation session is completed for the first time:

```python
from app.seeds.seed_versions import hook_into_validation_pipeline

# Hook into your validation completion logic
def on_validation_complete(db: Session, session: ValidationSession):
    # Your existing validation logic
    session.status = SessionStatus.COMPLETED
    db.commit()

    # Auto-create V1 if this is the first validation
    hook_into_validation_pipeline(db, session)
```

### Manual Version Creation

For amendments or manual uploads:

```python
from app.seeds.seed_versions import VersionSeeder

version = VersionSeeder.seed_version_manually(
    db=db,
    lc_number="BD-2024-001",
    user_id=user.id,
    session_id=session.id,
    files=[{"name": "amendment.pdf", "size": 2048}]
)
```

## Integration Flow

### Frontend Integration

1. **Upload Page**: Check if LC exists using `/lc/{lc_number}/check`
2. **Show Amendment Warning**: If `exists: true`, display amber warning
3. **Results Page**: Load versions using `/lc/{lc_number}/versions`
4. **Version Dropdown**: Allow switching between versions
5. **Comparison Dialog**: Compare versions using `/lc/{lc_number}/versions/compare`
6. **Dashboard**: Show amended LCs using `/lc/amended`

### Backend Integration

1. **Validation Pipeline**: Hook `seed_versions.py` into completion logic
2. **File Upload**: Create versions when new files are uploaded
3. **Status Updates**: Update version status through the validation lifecycle

## Testing

Run the comprehensive test suite:

```bash
# Run all version control tests
pytest tests/test_lc_versions.py -v

# Run specific test categories
pytest tests/test_lc_versions.py::TestLCVersionCRUD -v
pytest tests/test_lc_versions.py::TestVersionSeeder -v
pytest tests/test_lc_versions.py::TestLCVersionsAPI -v
```

### Test Coverage

The test suite covers:

- ✅ Creating V1 automatically
- ✅ Creating V2+ amendments
- ✅ Version listing and ordering
- ✅ Version comparison with discrepancy diff
- ✅ LC existence checking
- ✅ Amendment listing
- ✅ API endpoint functionality
- ✅ Authentication and authorization
- ✅ Error handling and edge cases

## Database Migration

To apply the version control schema:

```bash
# Run the migration
alembic upgrade head

# Verify migration
alembic history
alembic current
```

## Error Handling

### Common Error Scenarios

1. **Duplicate Version**: Returns 400 with constraint violation details
2. **LC Not Found**: Returns 404 for comparison/version requests
3. **Invalid Version Format**: Returns 400 for malformed version strings
4. **Session Not Found**: Returns 404 when validation session doesn't exist
5. **Unauthorized Access**: Returns 401/403 for authentication issues

### Error Response Format

```json
{
  "error": "ValidationError",
  "message": "Version V3 not found for LC BD-2024-001",
  "timestamp": "2024-01-15T10:30:00Z",
  "path": "/lc/BD-2024-001/versions/compare",
  "method": "GET"
}
```

## Performance Considerations

### Indexing Strategy

- **Primary Index**: `lc_number` for fast LC lookups
- **Composite Index**: `(lc_number, version)` for unique constraint and sorting
- **Temporal Index**: `created_at` for chronological queries
- **Status Index**: `status` for filtering by validation state

### Query Optimization

- Use pagination for large version lists
- Implement caching for frequently accessed comparisons
- Consider read replicas for reporting queries

### Scaling Recommendations

- Partition by `lc_number` prefix for large datasets
- Archive old versions to separate storage
- Implement background jobs for complex comparisons

## Security

### Authentication

All endpoints require valid JWT tokens with appropriate scopes.

### Authorization

- Users can only access versions for LCs they have permissions to view
- Version creation requires `write` permissions
- Admin users can access all versions

### Data Protection

- File metadata is stored securely with audit trails
- Sensitive LC information is encrypted at rest
- API calls are logged for compliance

## Monitoring and Observability

### Key Metrics

- Version creation rate
- Comparison request frequency
- Amendment detection accuracy
- API response times

### Logging

The system logs:
- Version creation events
- Comparison requests
- Error conditions
- Performance metrics

### Alerting

Set up alerts for:
- Failed version creations
- Unusual comparison patterns
- API performance degradation
- Database constraint violations