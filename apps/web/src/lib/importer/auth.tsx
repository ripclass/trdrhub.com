/**
 * Importer Authentication Hook and Context
 *
 * Provides authentication state management for importer users with predefined credentials.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface ImporterUser {
  id: string;
  name: string;
  email: string;
  role: 'importer' | 'tenant_admin';
  avatar?: string;
  company_id?: string;
}

interface ImporterAuthContext {
  user: ImporterUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const ImporterAuthContext = createContext<ImporterAuthContext | undefined>(undefined);

// Export context for direct useContext usage
export { ImporterAuthContext };

// Mock importer users for development
export const MOCK_IMPORTER_USERS = [
  {
    id: 'importer_user_1',
    name: 'David Lee',
    email: 'importer1@globalimports.com',
    role: 'importer' as const,
    avatar: undefined,
    password: 'importer123',
    company_id: 'company_importer_1'
  },
  {
    id: 'importer_user_2',
    name: 'Jennifer Brown',
    email: 'importer2@globalimports.com',
    role: 'importer' as const,
    avatar: undefined,
    password: 'importer123',
    company_id: 'company_importer_2'
  },
  {
    id: 'importer_user_3',
    name: 'Michael Johnson',
    email: 'admin@globalimports.com',
    role: 'tenant_admin' as const,
    avatar: undefined,
    password: 'admin123',
    company_id: 'company_importer_1'
  },
  {
    id: 'importer_user_4',
    name: 'Emily Davis',
    email: 'manager@globalimports.com',
    role: 'tenant_admin' as const,
    avatar: undefined,
    password: 'manager123',
    company_id: 'company_importer_1'
  },
];

// Mock login for development
export const mockImporterLogin = async (email: string, password: string) => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000));

  const user = MOCK_IMPORTER_USERS.find(u => u.email === email && u.password === password);
  if (!user) {
    throw new Error('Invalid credentials');
  }

  const { password: _, ...userWithoutPassword } = user;
  const token = `importer_token_${user.id}_${Date.now()}`;

  return {
    user: userWithoutPassword,
    token
  };
};

// Mock auth check for development
export const mockImporterAuthCheck = async (token: string): Promise<ImporterUser> => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));

  // Extract user ID from token
  const userIdMatch = token.match(/importer_token_(importer_user_\d+)_/);
  if (!userIdMatch) {
    throw new Error('Invalid token');
  }

  const userId = userIdMatch[1];
  const user = MOCK_IMPORTER_USERS.find(u => u.id === userId);
  if (!user) {
    throw new Error('User not found');
  }

  const { password: _, ...userWithoutPassword } = user;
  return userWithoutPassword;
};

interface ImporterAuthProviderProps {
  children: React.ReactNode;
}

export function ImporterAuthProvider({ children }: ImporterAuthProviderProps) {
  const [user, setUser] = useState<ImporterUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // Check if user is authenticated and load user data
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('importer_token');
        if (!token) {
          setIsLoading(false);
          return;
        }

        // Use mock auth check instead of API call
        try {
          const userData = await mockImporterAuthCheck(token);
          setUser(userData);
        } catch (error) {
          // Invalid token
          localStorage.removeItem('importer_token');
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('importer_token');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      // Use mock login function instead of API call
      const { user: userData, token } = await mockImporterLogin(email, password);

      // Store token
      localStorage.setItem('importer_token', token);

      // Set user
      setUser(userData);

      // Redirect to dashboard
      navigate('/lcopilot/importer-dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('importer_token');
    setUser(null);
    navigate('/lcopilot/importer-dashboard/login');
  };

  const value: ImporterAuthContext = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
  };

  return (
    <ImporterAuthContext.Provider value={value}>
      {children}
    </ImporterAuthContext.Provider>
  );
}

export function useImporterAuth(): ImporterAuthContext {
  const context = useContext(ImporterAuthContext);
  if (context === undefined) {
    throw new Error('useImporterAuth must be used within an ImporterAuthProvider');
  }
  return context;
}

