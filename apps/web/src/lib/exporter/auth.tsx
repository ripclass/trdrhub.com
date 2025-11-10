/**
 * Exporter Authentication Hook and Context
 *
 * Provides authentication state management for exporter users with predefined credentials.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

interface ExporterUser {
  id: string;
  name: string;
  email: string;
  role: 'exporter' | 'tenant_admin';
  avatar?: string;
  company_id?: string;
}

interface ExporterAuthContext {
  user: ExporterUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const ExporterAuthContext = createContext<ExporterAuthContext | undefined>(undefined);

// Mock exporter users for development
export const MOCK_EXPORTER_USERS = [
  {
    id: 'exporter_user_1',
    name: 'John Smith',
    email: 'exporter1@globalexports.com',
    role: 'exporter' as const,
    avatar: undefined,
    password: 'exporter123',
    company_id: 'company_exporter_1'
  },
  {
    id: 'exporter_user_2',
    name: 'Maria Garcia',
    email: 'exporter2@globalexports.com',
    role: 'exporter' as const,
    avatar: undefined,
    password: 'exporter123',
    company_id: 'company_exporter_2'
  },
  {
    id: 'exporter_user_3',
    name: 'Robert Chen',
    email: 'admin@globalexports.com',
    role: 'tenant_admin' as const,
    avatar: undefined,
    password: 'admin123',
    company_id: 'company_exporter_1'
  },
  {
    id: 'exporter_user_4',
    name: 'Sarah Williams',
    email: 'manager@globalexports.com',
    role: 'tenant_admin' as const,
    avatar: undefined,
    password: 'manager123',
    company_id: 'company_exporter_1'
  },
];

// Mock login for development
export const mockExporterLogin = async (email: string, password: string) => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000));

  const user = MOCK_EXPORTER_USERS.find(u => u.email === email && u.password === password);
  if (!user) {
    throw new Error('Invalid credentials');
  }

  const { password: _, ...userWithoutPassword } = user;
  const token = `exporter_token_${user.id}_${Date.now()}`;

  return {
    user: userWithoutPassword,
    token
  };
};

// Mock auth check for development
export const mockExporterAuthCheck = async (token: string): Promise<ExporterUser> => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));

  // Extract user ID from token
  const userIdMatch = token.match(/exporter_token_(exporter_user_\d+)_/);
  if (!userIdMatch) {
    throw new Error('Invalid token');
  }

  const userId = userIdMatch[1];
  const user = MOCK_EXPORTER_USERS.find(u => u.id === userId);
  if (!user) {
    throw new Error('User not found');
  }

  const { password: _, ...userWithoutPassword } = user;
  return userWithoutPassword;
};

interface ExporterAuthProviderProps {
  children: React.ReactNode;
}

export function ExporterAuthProvider({ children }: ExporterAuthProviderProps) {
  const [user, setUser] = useState<ExporterUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // Check if user is authenticated and load user data
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('exporter_token');
        if (!token) {
          setIsLoading(false);
          return;
        }

        // Use mock auth check instead of API call
        try {
          const userData = await mockExporterAuthCheck(token);
          setUser(userData);
        } catch (error) {
          // Invalid token
          localStorage.removeItem('exporter_token');
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('exporter_token');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      // Use mock login function instead of API call
      const { user: userData, token } = await mockExporterLogin(email, password);

      // Store token
      localStorage.setItem('exporter_token', token);

      // Set user
      setUser(userData);

      // Redirect to dashboard
      navigate('/lcopilot/exporter-dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('exporter_token');
    setUser(null);
    navigate('/lcopilot/exporter-dashboard/login');
  };

  const value: ExporterAuthContext = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
  };

  return (
    <ExporterAuthContext.Provider value={value}>
      {children}
    </ExporterAuthContext.Provider>
  );
}

export function useExporterAuth(): ExporterAuthContext {
  const context = useContext(ExporterAuthContext);
  if (context === undefined) {
    throw new Error('useExporterAuth must be used within an ExporterAuthProvider');
  }
  return context;
}

