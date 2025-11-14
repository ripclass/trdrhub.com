/**
 * Admin Authentication Hook and Context
 *
 * Provides authentication state management for admin users with RBAC.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/api/client';

interface AdminUser {
  id: string;
  name: string | null;
  email: string;
  role: string;
}

interface AdminAuthContext {
  user: AdminUser | null;
  permissions: string[];
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
}

const AdminAuthContext = createContext<AdminAuthContext | undefined>(undefined);

// Export context for direct useContext usage
export { AdminAuthContext };

const ADMIN_ALLOWED_ROLES = new Set(['system_admin', 'tenant_admin']);

const ROLE_PERMISSIONS: Record<string, string[]> = {
  system_admin: ['*'],
  tenant_admin: [
    'ops:read',
    'ops:write',
    'jobs:read',
    'jobs:write',
    'monitoring:read',
    'feature_flags:read',
    'feature_flags:write',
    'billing:read',
    'billing:write',
    'users:read',
  ],
};

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://trdrhub-api.onrender.com';

interface AdminAuthProviderProps {
  children: React.ReactNode;
}

export function AdminAuthProvider({ children }: AdminAuthProviderProps) {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const buildPermissions = useCallback((role: string | undefined | null) => {
    if (!role) return [];
    if (ROLE_PERMISSIONS[role]) {
      return ROLE_PERMISSIONS[role];
    }
    if (role === 'system_admin') return ['*'];
    return [];
  }, []);

  const fetchAdminProfile = useCallback(async (): Promise<AdminUser | null> => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('trdrhub_api_token');
      if (!token) {
        setUser(null);
        setPermissions([]);
        return null;
      }

      const response = await api.get('/auth/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const profile = response.data;
      if (!ADMIN_ALLOWED_ROLES.has(profile.role)) {
        localStorage.removeItem('trdrhub_api_token');
        setUser(null);
        setPermissions([]);
        throw new Error('This account does not have admin permissions.');
      }

      const adminUser: AdminUser = {
        id: profile.id,
        name: profile.full_name,
        email: profile.email,
        role: profile.role,
      };

      setUser(adminUser);
      setPermissions(buildPermissions(profile.role));
      return adminUser;
    } catch (error) {
      console.error('Admin auth check failed:', error);
      localStorage.removeItem('trdrhub_api_token');
      setUser(null);
      setPermissions([]);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [buildPermissions]);

  useEffect(() => {
    const token = localStorage.getItem('trdrhub_api_token');
    if (!token) {
      setIsLoading(false);
      return;
    }

    fetchAdminProfile().catch(() => {
      // handled in fetchAdminProfile
    });
  }, [fetchAdminProfile]);

  const login = async (email: string, password: string) => {
    try {
      setIsLoading(true);
      const response = await api.post(
        '/auth/login',
        { email, password },
        {
          baseURL: API_BASE_URL,
        },
      );

      const { access_token: accessToken } = response.data || {};
      if (!accessToken) {
        throw new Error('Authentication failed. No access token returned.');
      }

      localStorage.setItem('trdrhub_api_token', accessToken);
      await fetchAdminProfile();
      navigate('/admin');
    } catch (error) {
      console.error('Login failed:', error);
      localStorage.removeItem('trdrhub_api_token');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('trdrhub_api_token');
    setUser(null);
    setPermissions([]);
    navigate('/admin/login');
  };

  const checkPermission = (permission: string): boolean => {
    if (permissions.includes('*')) return true;
    return permissions.includes(permission);
  };

  const hasAnyPermission = (requiredPermissions: string[]): boolean => {
    if (permissions.includes('*')) return true;
    return requiredPermissions.some(permission => permissions.includes(permission));
  };

  const value: AdminAuthContext = {
    user,
    permissions,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
    checkPermission,
    hasAnyPermission
  };

  return (
    <AdminAuthContext.Provider value={value}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  const context = useContext(AdminAuthContext);
  if (context === undefined) {
    throw new Error('useAdminAuth must be used within an AdminAuthProvider');
  }
  return context;
}

// Higher-order component for permission checking
export function withAdminPermissions<P extends object>(
  Component: React.ComponentType<P>,
  requiredPermissions: string[]
) {
  return function PermissionWrappedComponent(props: P) {
    const { hasAnyPermission } = useAdminAuth();

    if (!hasAnyPermission(requiredPermissions)) {
      return (
        <div className="p-8 text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Access Denied
          </h2>
          <p className="text-gray-600">
            You don't have permission to access this feature.
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Required permissions: {requiredPermissions.join(', ')}
          </p>
        </div>
      );
    }

    return <Component {...props} />;
  };
}