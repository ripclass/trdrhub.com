/**
 * useUserRole - Hook for role-based access control
 * 
 * This hook fetches the current user's role and permissions from the API
 * and provides helper functions for checking access.
 * 
 * Usage:
 * const { role, isOwner, canManageTeam, canAccessTool } = useUserRole();
 * 
 * {canManageTeam && <Link to="/hub/team">Team</Link>}
 * {canAccessTool("price_verify") && <ToolCard />}
 */

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "./use-auth";

// Types
export type MemberRole = "owner" | "admin" | "member" | "viewer";

export interface UserPermissions {
  manage_team: boolean;
  remove_members: boolean;
  transfer_ownership: boolean;
  view_billing: boolean;
  manage_billing: boolean;
  view_usage: boolean;
  view_org_usage: boolean;
  access_all_tools: boolean;
  admin_panels: boolean;
  api_access: boolean;
}

export interface UserRoleData {
  user_id: string;
  company_id: string;
  role: MemberRole;
  tool_access: string[];
  permissions: UserPermissions;
  is_owner: boolean;
  is_admin: boolean;
  can_manage_team: boolean;
  can_view_billing: boolean;
  can_manage_billing: boolean;
}

// Default permissions for when not authenticated
const DEFAULT_PERMISSIONS: UserPermissions = {
  manage_team: false,
  remove_members: false,
  transfer_ownership: false,
  view_billing: false,
  manage_billing: false,
  view_usage: false,
  view_org_usage: false,
  access_all_tools: false,
  admin_panels: false,
  api_access: false,
};

// All available tools
export const ALL_TOOLS = [
  "lcopilot",
  "price_verify",
  "hscode",
  "sanctions",
  "container_track",
] as const;

export type ToolId = typeof ALL_TOOLS[number];

// Hook return type
export interface UseUserRoleReturn {
  // Loading state
  isLoading: boolean;
  error: string | null;
  
  // Role info
  role: MemberRole | null;
  companyId: string | null;
  
  // Role checks
  isOwner: boolean;
  isAdmin: boolean;
  isMember: boolean;
  isViewer: boolean;
  
  // Permission checks
  canManageTeam: boolean;
  canViewBilling: boolean;
  canManageBilling: boolean;
  canViewUsage: boolean;
  canViewOrgUsage: boolean;
  canAccessAdminPanels: boolean;
  canAccessApi: boolean;
  
  // Tool access
  toolAccess: string[];
  canAccessTool: (toolId: string) => boolean;
  canAccessAnyTool: boolean;
  
  // Raw permissions
  permissions: UserPermissions;
  
  // Refresh
  refresh: () => Promise<void>;
}

export function useUserRole(): UseUserRoleReturn {
  const { user, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [roleData, setRoleData] = useState<UserRoleData | null>(null);

  const fetchPermissions = useCallback(async () => {
    if (!user) {
      setRoleData(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch("/api/members/me/permissions", {
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
      });

      if (!response.ok) {
        // User might not be part of a company yet
        if (response.status === 403) {
          // No company membership - treat as basic user
          setRoleData({
            user_id: user.id,
            company_id: "",
            role: "member",
            tool_access: [],
            permissions: DEFAULT_PERMISSIONS,
            is_owner: false,
            is_admin: false,
            can_manage_team: false,
            can_view_billing: false,
            can_manage_billing: false,
          });
          return;
        }
        throw new Error("Failed to fetch permissions");
      }

      const data = await response.json();
      setRoleData(data);
    } catch (err) {
      console.error("Failed to fetch user role:", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      // Set default permissions on error
      setRoleData(null);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!authLoading) {
      fetchPermissions();
    }
  }, [authLoading, fetchPermissions]);

  // Computed values
  const role = roleData?.role ?? null;
  const isOwner = roleData?.is_owner ?? false;
  const isAdmin = roleData?.is_admin ?? false;
  const isMember = role === "member";
  const isViewer = role === "viewer";
  
  const permissions = roleData?.permissions ?? DEFAULT_PERMISSIONS;
  const toolAccess = roleData?.tool_access ?? [];

  const canAccessTool = useCallback(
    (toolId: string): boolean => {
      if (!roleData) return false;
      // Owner/Admin can access all tools
      if (isOwner || isAdmin) return true;
      return toolAccess.includes(toolId);
    },
    [roleData, isOwner, isAdmin, toolAccess]
  );

  return {
    // Loading state
    isLoading: isLoading || authLoading,
    error,
    
    // Role info
    role,
    companyId: roleData?.company_id ?? null,
    
    // Role checks
    isOwner,
    isAdmin,
    isMember,
    isViewer,
    
    // Permission checks
    canManageTeam: roleData?.can_manage_team ?? false,
    canViewBilling: roleData?.can_view_billing ?? false,
    canManageBilling: roleData?.can_manage_billing ?? false,
    canViewUsage: permissions.view_usage,
    canViewOrgUsage: permissions.view_org_usage,
    canAccessAdminPanels: permissions.admin_panels,
    canAccessApi: permissions.api_access,
    
    // Tool access
    toolAccess,
    canAccessTool,
    canAccessAnyTool: isOwner || isAdmin || toolAccess.length > 0,
    
    // Raw permissions
    permissions,
    
    // Refresh
    refresh: fetchPermissions,
  };
}


