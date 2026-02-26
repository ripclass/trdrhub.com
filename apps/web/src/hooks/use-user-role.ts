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

// API base URL - use env var or fallback to production
const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

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

// All available tools - must match tool IDs in HubHome.tsx
export const ALL_TOOLS = [
  "lcopilot",
  "lc_builder",
  "doc-generator",
  "sanctions",
  "hs_code",
  "container",
  "price_verify",
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

    // Build owner-level fallback role data used when RBAC endpoint is unavailable.
    // Private-beta: all users get full access until RBAC is fully propagated.
    const ownerFallback: UserRoleData = {
      user_id: user.id,
      company_id: "",
      role: "owner",
      tool_access: ALL_TOOLS as unknown as string[],
      permissions: {
        ...DEFAULT_PERMISSIONS,
        manage_team: true,
        view_billing: true,
        manage_billing: true,
        view_usage: true,
        view_org_usage: true,
        access_all_tools: true,
        admin_panels: true,
        api_access: true,
      },
      is_owner: true,
      is_admin: true,
      can_manage_team: true,
      can_view_billing: true,
      can_manage_billing: true,
    };

    try {
      setIsLoading(true);
      setError(null);

      // Attach Supabase JWT so the request is authenticated even without cookies.
      let authHeaders: Record<string, string> = { "Content-Type": "application/json" };
      try {
        const { supabase } = await import("@/lib/supabase");
        const { data: sessionData } = await supabase.auth.getSession();
        const token = sessionData?.session?.access_token;
        if (token) {
          authHeaders["Authorization"] = `Bearer ${token}`;
        }
      } catch {
        // Non-critical — fall through without auth header
      }

      const response = await fetch(`${API_BASE}/members/me/permissions`, {
        headers: authHeaders,
        credentials: "include",
      });

      if (!response.ok) {
        // 401/403/404 → user not in RBAC yet (legacy user) — treat as owner.
        // This prevents a spurious redirect-to-login when the RBAC record hasn't
        // been created yet for a user that authenticated successfully via Supabase.
        if (response.status === 401 || response.status === 403 || response.status === 404) {
          setRoleData(ownerFallback);
          return;
        }
        throw new Error("Failed to fetch permissions");
      }

      const data = await response.json();
      setRoleData(data);
    } catch (err) {
      console.error("Failed to fetch user role:", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      // On any error, default to owner-level access so the UI remains usable.
      // This prevents blank/bouncing states when the permissions API is unreachable.
      setRoleData(ownerFallback);
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


