# LCopilot RBAC Authentication Integration

This document describes the comprehensive Role-Based Access Control (RBAC) system implemented for LCopilot's FastAPI backend.

## Overview

LCopilot now supports four distinct user roles with clearly defined permissions:
- **Exporter**: Can upload/validate documents and manage their own data
- **Importer**: Same permissions as Exporter
- **Bank**: Read-only access to all system data for compliance monitoring
- **Admin**: Full system access including user management

## Architecture Components

### 1. Database Schema

**User Role Column**
```sql
ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'exporter'
CHECK (role IN ('exporter','importer','bank','admin'));
```

The role is stored directly in the database and validated on every request.

### 2. JWT Token Structure

JWT tokens now include role claims that are validated against the database:

```json
{
  "sub": "user_uuid",
  "role": "exporter",
  "email": "user@example.com",
  "exp": 1640995200,
  "iat": 1640991600
}
```

**Security**: Role tampering is prevented by validating JWT role against database role on every request.

### 3. Permission Matrix

The system uses a comprehensive permissions matrix defined in `app/core/rbac.py`:

| Permission | Exporter | Importer | Bank | Admin |
|------------|----------|----------|------|-------|
| Upload/Validate Documents | ✓ | ✓ | ✗ | ✓ |
| View Own Jobs | ✓ | ✓ | ✗ | ✓ |
| View All Jobs | ✗ | ✗ | ✓ | ✓ |
| Download Evidence | ✓ | ✓ | ✓ | ✓ |
| View Audit Logs | Own Only | Own Only | All | All |
| Generate Compliance Reports | ✗ | ✗ | ✓ | ✓ |
| Manage Users/Roles | ✗ | ✗ | ✗ | ✓ |
| System Administration | ✗ | ✗ | ✗ | ✓ |

### 4. Security Modules

#### `app/core/security.py`
- JWT creation and validation with role claims
- Authentication dependencies (`get_current_user`, `require_admin`, etc.)
- Password hashing and user authentication
- Role validation against database to prevent tampering

#### `app/core/rbac.py`
- `RBACPolicyEngine`: Core policy enforcement
- Permission enums and role mapping
- Resource ownership validation
- Endpoint-specific permission mapping

### 5. Authentication Flow

1. **Login**: User provides credentials
2. **Token Creation**: JWT created with user ID, role, and expiration
3. **Token Validation**: On each request:
   - JWT is decoded and validated
   - User is fetched from database
   - JWT role is compared with database role
   - Access is granted/denied based on permissions

## API Endpoints

### Authentication Endpoints (`/auth`)

```bash
POST /auth/register     # Register new user (default: exporter role)
POST /auth/login        # Authenticate and receive JWT token
GET  /auth/me          # Get current user profile
```

### Protected Endpoints

All protected endpoints now enforce role-based permissions:

#### Session Management (`/sessions`)
```bash
POST /sessions              # Create session (exporter, importer, admin)
GET  /sessions              # List sessions (role-filtered)
GET  /sessions/{id}         # View session (owner or privileged)
GET  /sessions/{id}/report  # Download report (owner or privileged)
```

#### Document Processing (`/documents`)
```bash
POST /documents/process-document  # Upload/process (exporter, importer, admin)
```

#### Admin Endpoints (`/admin`)
```bash
GET  /admin/users                    # List users (admin only)
POST /admin/users                    # Create user (admin only)
PUT  /admin/users/{id}/role          # Update role (admin only)
PUT  /admin/users/{id}/deactivate    # Deactivate user (admin only)
GET  /admin/users/stats              # User statistics (admin only)
GET  /admin/roles/permissions        # View permissions matrix (admin only)
```

#### Audit Endpoints (`/admin/audit`)
```bash
GET /admin/audit/logs                # View audit logs (bank, admin)
GET /admin/audit/compliance-report   # Generate reports (bank, admin)
GET /admin/audit/statistics          # Audit metrics (bank, admin)
```

## Implementation Details

### Role-Based Route Protection

Three patterns are used to protect endpoints:

1. **Permission Checking**:
```python
if not RBACPolicyEngine.has_permission(user.role, Permission.UPLOAD_OWN_DOCS):
    raise HTTPException(status_code=403, detail="Insufficient permissions")
```

2. **Dependency Injection**:
```python
@router.get("/admin-only")
async def admin_endpoint(user: User = Depends(require_admin)):
    # Only admins can access this
```

3. **Resource Ownership**:
```python
if not RBACPolicyEngine.can_access_resource(
    user_role=current_user.role,
    resource_owner_id=str(session.user_id),
    user_id=str(current_user.id),
    permission=Permission.VIEW_OWN_JOBS
):
    raise HTTPException(status_code=403, detail="Access denied")
```

### Data Filtering

Users see different data based on their role:

- **Exporters/Importers**: Only their own sessions, documents, and audit logs
- **Banks**: All sessions and audit logs (read-only)
- **Admins**: All data with full access

Example implementation:
```python
if current_user.role in ["bank", "admin"]:
    sessions = session_service.get_all_sessions()
else:
    sessions = session_service.get_user_sessions(current_user)
```

### Security Features

1. **JWT Role Validation**: Prevents client-side role tampering
2. **Database Consistency**: Role stored in database, not just JWT
3. **Audit Logging**: All role changes and access attempts are logged
4. **Permission Inheritance**: Higher roles inherit lower role permissions
5. **Resource Ownership**: Users can only access their own resources (unless privileged)

## Testing

Comprehensive test suite in `tests/test_rbac.py` covers:

- Permission matrix validation for all roles
- Endpoint access control enforcement
- JWT token validation and role tampering prevention
- Resource ownership and data filtering
- Authentication flow testing

Run tests:
```bash
pytest tests/test_rbac.py -v
```

## Usage Examples

### Creating Users with Roles

**Admin Creating User**:
```python
POST /admin/users
{
    "email": "trader@example.com",
    "password": "secure123",
    "full_name": "John Trader",
    "role": "exporter"
}
```

**Self Registration (Default Exporter)**:
```python
POST /auth/register
{
    "email": "trader@example.com",
    "password": "secure123",
    "full_name": "John Trader"
}
```

### Changing User Roles

Only admins can modify user roles:
```python
PUT /admin/users/{user_id}/role
{
    "user_id": "uuid-here",
    "role": "bank",
    "reason": "Promoted to bank oversight role"
}
```

### Accessing Protected Resources

All requests must include JWT token:
```bash
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Migration Guide

### Existing Users
- All existing users default to "exporter" role
- Admins must manually assign appropriate roles via `/admin/users/{id}/role`

### Existing Code
- Replace `get_current_user` imports:
  ```python
  # Old
  from ..auth import get_current_user

  # New
  from ..core.security import get_current_user
  ```

- Add permission checks to sensitive operations:
  ```python
  if not RBACPolicyEngine.has_permission(user.role, Permission.ADMIN_ACCESS):
      raise HTTPException(status_code=403)
  ```

## Configuration

### Environment Variables

```bash
# JWT Configuration (existing)
JWT_SECRET_KEY=your-secret-key-here
JWT_EXPIRATION_HOURS=24

# Database (existing)
DATABASE_URL=postgresql://user:pass@localhost/lcopilot
```

### Default Settings

- New users: `exporter` role by default
- JWT expiration: 24 hours
- Permission validation: Strict (no fallback permissions)
- Audit logging: All role changes and access attempts

## Security Considerations

1. **Secret Management**: Use strong, unique JWT secrets in production
2. **Role Assignment**: Carefully control who has admin access
3. **Token Expiration**: Consider shorter expiration for sensitive roles
4. **Audit Trail**: Monitor role changes and access patterns
5. **Database Consistency**: Role stored in DB prevents client tampering
6. **HTTPS Only**: Always use HTTPS in production for token security

## Troubleshooting

### Common Issues

1. **403 Forbidden**: Check user role and required permissions
2. **401 Unauthorized**: Verify JWT token validity and user status
3. **Role Mismatch**: Ensure JWT role matches database role
4. **Permission Denied**: Confirm user has required permission for action

### Debugging

Enable detailed logging to trace permission checks:
```python
import logging
logging.getLogger("app.core.rbac").setLevel(logging.DEBUG)
```

## Future Enhancements

Potential extensions to the RBAC system:

1. **Custom Roles**: Allow creating custom roles with specific permissions
2. **Time-Based Access**: Roles that expire after a certain time
3. **IP Restrictions**: Limit admin access to specific IP ranges
4. **Multi-Factor Auth**: Require MFA for admin role elevation
5. **Resource-Level Permissions**: More granular permissions per resource type
6. **Role Hierarchies**: More complex role inheritance patterns

---

For technical support or questions about the RBAC implementation, please refer to the development team or create an issue in the project repository.