"""
Role-Based Access Control (RBAC) implementation.

This module contains the permissions matrix and policy enforcement
for LCopilot's user roles system.
"""

from enum import Enum
from typing import Dict, List, Set
from ..models import UserRole


class Permission(str, Enum):
    """System permissions for RBAC."""
    # Document operations
    UPLOAD_OWN_DOCS = "upload_own_docs"
    VALIDATE_OWN_DOCS = "validate_own_docs"
    DOWNLOAD_OWN_EVIDENCE = "download_own_evidence"

    # Job/Session operations
    VIEW_OWN_JOBS = "view_own_jobs"
    VIEW_ALL_JOBS = "view_all_jobs"
    CREATE_JOBS = "create_jobs"
    DELETE_OWN_JOBS = "delete_own_jobs"

    # Audit operations
    VIEW_OWN_AUDIT_LOGS = "view_own_audit_logs"
    VIEW_ALL_AUDIT_LOGS = "view_all_audit_logs"
    EXPORT_AUDIT_LOGS = "export_audit_logs"

    # Compliance operations
    GENERATE_COMPLIANCE_REPORTS = "generate_compliance_reports"
    VIEW_SYSTEM_METRICS = "view_system_metrics"

    # User management
    VIEW_USERS = "view_users"
    MANAGE_ROLES = "manage_roles"
    DEACTIVATE_USERS = "deactivate_users"

    # System administration
    ADMIN_ACCESS = "admin_access"
    SYSTEM_MONITORING = "system_monitoring"
    MANAGE_SYSTEM_CONFIG = "manage_system_config"


# PERMISSIONS MATRIX - Single Source of Truth
# This matrix defines exactly what each role can do
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.EXPORTER: {
        Permission.UPLOAD_OWN_DOCS,
        Permission.VALIDATE_OWN_DOCS,
        Permission.DOWNLOAD_OWN_EVIDENCE,
        Permission.VIEW_OWN_JOBS,
        Permission.CREATE_JOBS,
        Permission.DELETE_OWN_JOBS,
        Permission.VIEW_OWN_AUDIT_LOGS,
    },

    UserRole.IMPORTER: {
        Permission.UPLOAD_OWN_DOCS,
        Permission.VALIDATE_OWN_DOCS,
        Permission.DOWNLOAD_OWN_EVIDENCE,
        Permission.VIEW_OWN_JOBS,
        Permission.CREATE_JOBS,
        Permission.DELETE_OWN_JOBS,
        Permission.VIEW_OWN_AUDIT_LOGS,
    },

    UserRole.BANK: {
        # Banks have read access to system-wide data for compliance
        Permission.VIEW_ALL_JOBS,
        Permission.VIEW_ALL_AUDIT_LOGS,
        Permission.EXPORT_AUDIT_LOGS,
        Permission.GENERATE_COMPLIANCE_REPORTS,
        Permission.VIEW_SYSTEM_METRICS,
        Permission.SYSTEM_MONITORING,
        Permission.VIEW_USERS,
        # Banks can also download evidence packs by policy
        Permission.DOWNLOAD_OWN_EVIDENCE,
    },

    UserRole.ADMIN: {
        # Admins have all permissions
        Permission.UPLOAD_OWN_DOCS,
        Permission.VALIDATE_OWN_DOCS,
        Permission.DOWNLOAD_OWN_EVIDENCE,
        Permission.VIEW_OWN_JOBS,
        Permission.VIEW_ALL_JOBS,
        Permission.CREATE_JOBS,
        Permission.DELETE_OWN_JOBS,
        Permission.VIEW_OWN_AUDIT_LOGS,
        Permission.VIEW_ALL_AUDIT_LOGS,
        Permission.EXPORT_AUDIT_LOGS,
        Permission.GENERATE_COMPLIANCE_REPORTS,
        Permission.VIEW_SYSTEM_METRICS,
        Permission.VIEW_USERS,
        Permission.MANAGE_ROLES,
        Permission.DEACTIVATE_USERS,
        Permission.ADMIN_ACCESS,
        Permission.SYSTEM_MONITORING,
        Permission.MANAGE_SYSTEM_CONFIG,
    }
}


class RBACPolicyEngine:
    """Policy engine for role-based access control."""

    @staticmethod
    def has_permission(user_role: str, permission: Permission) -> bool:
        """
        Check if a role has a specific permission.

        Args:
            user_role: User's role as string
            permission: Permission to check

        Returns:
            True if role has permission
        """
        try:
            role_enum = UserRole(user_role)
            return permission in ROLE_PERMISSIONS.get(role_enum, set())
        except ValueError:
            # Invalid role
            return False

    @staticmethod
    def get_role_permissions(user_role: str) -> Set[Permission]:
        """
        Get all permissions for a role.

        Args:
            user_role: User's role as string

        Returns:
            Set of permissions for the role
        """
        try:
            role_enum = UserRole(user_role)
            return ROLE_PERMISSIONS.get(role_enum, set())
        except ValueError:
            return set()

    @staticmethod
    def can_access_resource(user_role: str, resource_owner_id: str, user_id: str, permission: Permission) -> bool:
        """
        Check if user can access a specific resource.

        This implements owner-based access control with role escalation.

        Args:
            user_role: User's role
            resource_owner_id: ID of resource owner
            user_id: Current user's ID
            permission: Required permission

        Returns:
            True if access allowed
        """
        # Check if role has the required permission
        if not RBACPolicyEngine.has_permission(user_role, permission):
            return False

        # For "own" permissions, check ownership or privileged access
        if permission in [
            Permission.VIEW_OWN_JOBS,
            Permission.VIEW_OWN_AUDIT_LOGS,
            Permission.DOWNLOAD_OWN_EVIDENCE,
            Permission.DELETE_OWN_JOBS
        ]:
            # Privileged roles (bank, admin) can access all resources
            if user_role in [UserRole.BANK, UserRole.ADMIN]:
                return True

            # Others can only access their own resources
            return user_id == resource_owner_id

        # For system-wide permissions, role permission is sufficient
        return True

    @staticmethod
    def filter_by_ownership(user_role: str, user_id: str, resources: List[dict], owner_field: str = "user_id") -> List[dict]:
        """
        Filter resources based on ownership and role permissions.

        Args:
            user_role: User's role
            user_id: Current user's ID
            resources: List of resources to filter
            owner_field: Field name containing owner ID

        Returns:
            Filtered list of resources
        """
        # Privileged roles see all resources
        if user_role in [UserRole.BANK, UserRole.ADMIN]:
            return resources

        # Others see only their own resources
        return [r for r in resources if str(r.get(owner_field)) == str(user_id)]


# Endpoint-specific permission mappings
ENDPOINT_PERMISSIONS = {
    # Session/Job endpoints
    "GET /sessions": Permission.VIEW_OWN_JOBS,
    "GET /sessions/{id}": Permission.VIEW_OWN_JOBS,
    "POST /sessions": Permission.CREATE_JOBS,
    "DELETE /sessions/{id}": Permission.DELETE_OWN_JOBS,
    "GET /sessions/{id}/report": Permission.DOWNLOAD_OWN_EVIDENCE,

    # Document endpoints
    "POST /documents/process": Permission.UPLOAD_OWN_DOCS,
    "POST /documents/{id}/validate": Permission.VALIDATE_OWN_DOCS,

    # Audit endpoints
    "GET /admin/audit/logs": Permission.VIEW_ALL_AUDIT_LOGS,
    "GET /admin/audit/user/{id}/activity": Permission.VIEW_OWN_AUDIT_LOGS,
    "GET /admin/audit/compliance-report": Permission.GENERATE_COMPLIANCE_REPORTS,
    "GET /admin/audit/statistics": Permission.VIEW_SYSTEM_METRICS,
    "GET /admin/audit/monitoring/health": Permission.SYSTEM_MONITORING,

    # User management endpoints
    "GET /users": Permission.VIEW_USERS,
    "POST /users/roles": Permission.MANAGE_ROLES,
    "PUT /users/{id}/deactivate": Permission.DEACTIVATE_USERS,

    # Admin endpoints
    "GET /admin/*": Permission.ADMIN_ACCESS,
}


def get_permission_for_endpoint(method: str, path: str) -> Permission:
    """
    Get required permission for an endpoint.

    Args:
        method: HTTP method
        path: Request path

    Returns:
        Required permission
    """
    endpoint_key = f"{method} {path}"

    # Check for exact match
    if endpoint_key in ENDPOINT_PERMISSIONS:
        return ENDPOINT_PERMISSIONS[endpoint_key]

    # Check for pattern matches
    for pattern, permission in ENDPOINT_PERMISSIONS.items():
        if "*" in pattern:
            pattern_parts = pattern.split("*")
            if len(pattern_parts) == 2:
                prefix, suffix = pattern_parts
                if endpoint_key.startswith(prefix) and endpoint_key.endswith(suffix):
                    return permission

    # Default to most restrictive permission
    return Permission.ADMIN_ACCESS


def get_role_capabilities() -> Dict[str, Dict[str, bool]]:
    """
    Get capabilities matrix for frontend display.

    Returns:
        Dictionary mapping roles to their capabilities
    """
    capabilities = {}

    for role in UserRole:
        role_permissions = ROLE_PERMISSIONS.get(role, set())

        capabilities[role.value] = {
            # Document operations
            "upload_validate_docs": Permission.UPLOAD_OWN_DOCS in role_permissions,
            "view_own_jobs": Permission.VIEW_OWN_JOBS in role_permissions,
            "view_all_jobs": Permission.VIEW_ALL_JOBS in role_permissions,
            "download_evidence": Permission.DOWNLOAD_OWN_EVIDENCE in role_permissions,

            # Audit and compliance
            "view_own_audit": Permission.VIEW_OWN_AUDIT_LOGS in role_permissions,
            "view_all_audit": Permission.VIEW_ALL_AUDIT_LOGS in role_permissions,
            "compliance_reports": Permission.GENERATE_COMPLIANCE_REPORTS in role_permissions,

            # Administration
            "manage_users": Permission.VIEW_USERS in role_permissions,
            "manage_roles": Permission.MANAGE_ROLES in role_permissions,
            "admin_access": Permission.ADMIN_ACCESS in role_permissions,
            "system_monitoring": Permission.SYSTEM_MONITORING in role_permissions,
        }

    return capabilities