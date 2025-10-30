/**
 * Admin Authentication Hook and Context
 *
 * Provides authentication state management for admin users with RBAC.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar?: string;
  organization_id?: string;
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

// Admin role permissions mapping
const ADMIN_PERMISSIONS = {
  super_admin: ['*'], // All permissions
  ops_admin: [
    'ops:read', 'ops:write',
    'jobs:read', 'jobs:write',
    'monitoring:read',
    'feature_flags:read', 'feature_flags:write',
    'users:read'
  ],
  security_admin: [
    'audit:read', 'audit:export',
    'users:read', 'users:write',
    'api_keys:read', 'api_keys:write',
    'sessions:read', 'sessions:write',
    'approvals:read', 'approvals:write',
    'break_glass:read'
  ],
  finance_admin: [
    'billing:read', 'billing:write',
    'credits:read', 'credits:write',
    'disputes:read', 'disputes:write',
    'approvals:read', 'approvals:write'
  ],
  partner_admin: [
    'partners:read', 'partners:write',
    'webhooks:read', 'webhooks:write',
    'integrations:read', 'integrations:write'
  ],
  compliance_admin: [
    'audit:read', 'audit:export',
    'data_residency:read', 'data_residency:write',
    'retention:read', 'retention:write',
    'legal_holds:read', 'legal_holds:write'
  ]
};

interface AdminAuthProviderProps {
  children: React.ReactNode;
}

export function AdminAuthProvider({ children }: AdminAuthProviderProps) {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // Check if user is authenticated and load user data
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('admin_token');
        if (!token) {
          setIsLoading(false);
          return;
        }

        // Use mock auth check instead of API call
        try {
          const userData = await mockAdminAuthCheck(token);
          setUser(userData);

          // Set permissions based on role
          const userPermissions = ADMIN_PERMISSIONS[userData.role as keyof typeof ADMIN_PERMISSIONS] || [];
          setPermissions(userPermissions);
        } catch (error) {
          // Invalid token
          localStorage.removeItem('admin_token');
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('admin_token');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      // Use mock login function instead of API call
      const { user: userData, token } = await mockAdminLogin(email, password);

      // Store token
      localStorage.setItem('admin_token', token);

      // Set user and permissions
      setUser(userData);
      const userPermissions = ADMIN_PERMISSIONS[userData.role as keyof typeof ADMIN_PERMISSIONS] || [];
      setPermissions(userPermissions);

      // Redirect to dashboard
      navigate('/admin');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('admin_token');
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

// Mock admin users for development
export const MOCK_ADMIN_USERS = [
  {
    id: 'admin_1',
    name: 'John Smith',
    email: 'admin@lcopilot.com',
    role: 'super_admin',
    avatar: undefined,
    password: 'admin123' // Only for demo
  },
  {
    id: 'admin_2',
    name: 'Sarah Johnson',
    email: 'ops@lcopilot.com',
    role: 'ops_admin',
    avatar: undefined,
    password: 'ops123'
  },
  {
    id: 'admin_3',
    name: 'Mike Chen',
    email: 'security@lcopilot.com',
    role: 'security_admin',
    avatar: undefined,
    password: 'security123'
  },
  {
    id: 'admin_4',
    name: 'Lisa Rodriguez',
    email: 'finance@lcopilot.com',
    role: 'finance_admin',
    avatar: undefined,
    password: 'finance123'
  }
];

// Mock login for development
export const mockAdminLogin = async (email: string, password: string) => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000));

  const user = MOCK_ADMIN_USERS.find(u => u.email === email && u.password === password);
  if (!user) {
    throw new Error('Invalid credentials');
  }

  const { password: _, ...userWithoutPassword } = user;
  const token = `mock_token_${user.id}_${Date.now()}`;

  return {
    user: userWithoutPassword,
    token
  };
};

// Mock auth check for development
export const mockAdminAuthCheck = async (token: string) => {
  if (!token.startsWith('mock_token_')) {
    throw new Error('Invalid token');
  }

  const userId = token.split('_')[2];
  const user = MOCK_ADMIN_USERS.find(u => u.id === userId);

  if (!user) {
    throw new Error('User not found');
  }

  const { password: _, ...userWithoutPassword } = user;
  return userWithoutPassword;
};