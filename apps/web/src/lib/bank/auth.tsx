/**
 * Bank Authentication Hook and Context
 *
 * Provides authentication state management for bank users with predefined credentials.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface BankUser {
  id: string;
  name: string;
  email: string;
  role: 'bank_officer' | 'bank_admin';
  avatar?: string;
  company_id?: string;
}

interface BankAuthContext {
  user: BankUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const BankAuthContext = createContext<BankAuthContext | undefined>(undefined);

// Mock bank users for development
export const MOCK_BANK_USERS = [
  {
    id: 'bank_user_1',
    name: 'Sarah Johnson',
    email: 'admin@bankone.com',
    role: 'bank_admin' as const,
    avatar: undefined,
    password: 'admin123' // Only for demo
  },
  {
    id: 'bank_user_2',
    name: 'Michael Chen',
    email: 'officer1@bankone.com',
    role: 'bank_officer' as const,
    avatar: undefined,
    password: 'officer123'
  },
  {
    id: 'bank_user_3',
    name: 'Emily Rodriguez',
    email: 'officer2@bankone.com',
    role: 'bank_officer' as const,
    avatar: undefined,
    password: 'officer123'
  },
  {
    id: 'bank_user_4',
    name: 'David Kumar',
    email: 'officer3@bankone.com',
    role: 'bank_officer' as const,
    avatar: undefined,
    password: 'officer123'
  },
  {
    id: 'bank_user_5',
    name: 'Lisa Anderson',
    email: 'manager@bankone.com',
    role: 'bank_admin' as const,
    avatar: undefined,
    password: 'manager123'
  }
];

// Mock login for development
export const mockBankLogin = async (email: string, password: string) => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000));

  const user = MOCK_BANK_USERS.find(u => u.email === email && u.password === password);
  if (!user) {
    throw new Error('Invalid credentials');
  }

  const { password: _, ...userWithoutPassword } = user;
  const token = `bank_token_${user.id}_${Date.now()}`;

  return {
    user: userWithoutPassword,
    token
  };
};

// Mock auth check for development
export const mockBankAuthCheck = async (token: string): Promise<BankUser> => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));

  // Extract user ID from token
  const userIdMatch = token.match(/bank_token_(bank_user_\d+)_/);
  if (!userIdMatch) {
    throw new Error('Invalid token');
  }

  const userId = userIdMatch[1];
  const user = MOCK_BANK_USERS.find(u => u.id === userId);
  if (!user) {
    throw new Error('User not found');
  }

  const { password: _, ...userWithoutPassword } = user;
  return userWithoutPassword;
};

interface BankAuthProviderProps {
  children: React.ReactNode;
}

export function BankAuthProvider({ children }: BankAuthProviderProps) {
  const [user, setUser] = useState<BankUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // Check if user is authenticated and load user data
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('bank_token');
        if (!token) {
          setIsLoading(false);
          return;
        }

        // Use mock auth check instead of API call
        try {
          const userData = await mockBankAuthCheck(token);
          setUser(userData);
        } catch (error) {
          // Invalid token
          localStorage.removeItem('bank_token');
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('bank_token');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      // Use mock login function instead of API call
      const { user: userData, token } = await mockBankLogin(email, password);

      // Store token
      localStorage.setItem('bank_token', token);

      // Set user
      setUser(userData);

      // Redirect to dashboard
      navigate('/lcopilot/bank-dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('bank_token');
    setUser(null);
    navigate('/lcopilot/bank-dashboard/login');
  };

  const value: BankAuthContext = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
  };

  return (
    <BankAuthContext.Provider value={value}>
      {children}
    </BankAuthContext.Provider>
  );
}

export function useBankAuth(): BankAuthContext {
  const context = useContext(BankAuthContext);
  if (context === undefined) {
    throw new Error('useBankAuth must be used within a BankAuthProvider');
  }
  return context;
}

