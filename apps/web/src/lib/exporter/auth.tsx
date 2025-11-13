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

// Export context for direct useContext usage
export { ExporterAuthContext };

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
        // First, check if main auth hook already has user (faster path)
        try {
          const { useAuth } = await import('@/hooks/use-auth');
          // Note: Can't use hooks conditionally, so we'll check localStorage/session instead
        } catch {}
        
        // First, try to get Supabase session token (use shared client instance) with timeout
        let token: string | null = null;
        
        try {
          // Import the shared Supabase client instead of creating a new one
          const { supabase } = await import('@/lib/supabase');
          
          // Add timeout to prevent hanging
          const sessionPromise = supabase.auth.getSession();
          const timeoutPromise = new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Session check timeout')), 3000)
          );
          
          const { data: sessionData } = await Promise.race([sessionPromise, timeoutPromise]) as any;
          token = sessionData?.session?.access_token || null;
        } catch (supabaseError: any) {
          console.warn('Failed to get Supabase session:', supabaseError?.message || supabaseError);
          // Continue to fallback
        }
        
        // Fallback: Check for API token (preferred) or exporter token
        if (!token) {
          token = localStorage.getItem('trdrhub_api_token') || localStorage.getItem('exporter_token');
        }
        
        // DEMO MODE: If no token, check main auth first before falling back to demo
        if (!token) {
          // Check if main auth (Supabase) has a session - if so, don't use demo user
          try {
            const { supabase } = await import('@/lib/supabase');
            const { data: { session } } = await supabase.auth.getSession();
            if (session?.access_token) {
              // Main auth has session, wait for it to load user instead of using demo
              setIsLoading(false);
              return;
            }
          } catch (supabaseError) {
            // Continue to demo check
          }
          
          const demoMode = localStorage.getItem('demo_mode') === 'true' || 
                          new URLSearchParams(window.location.search).get('demo') === 'true';
          
          if (demoMode) {
            const demoUser: ExporterUser = {
              id: 'demo@trdrhub.com',
              name: 'Demo User',
              email: 'demo@trdrhub.com',
              role: 'exporter',
            };
            setUser(demoUser);
            setIsLoading(false);
            return;
          }
          
          setIsLoading(false);
          return;
        }

        // Try to get user info from API with timeout
        try {
          const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
          
          const fetchPromise = fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
            credentials: 'include',
          });
          
          const timeoutPromise = new Promise((_, reject) => 
            setTimeout(() => reject(new Error('API timeout')), 10000)
          );
          
          const response = await Promise.race([fetchPromise, timeoutPromise]) as Response;

          if (response.ok) {
            const userData = await response.json();
            setUser({
              id: userData.id || userData.email,
              name: userData.full_name || userData.name || userData.email.split('@')[0],
              email: userData.email,
              role: userData.role === 'tenant_admin' ? 'tenant_admin' : 'exporter',
              company_id: userData.company_id,
            });
          } else {
            // Token invalid, clear it
            localStorage.removeItem('exporter_token');
            localStorage.removeItem('trdrhub_api_token');
          }
        } catch (error: any) {
          console.warn('API call failed or timed out:', error?.message || error);
          // If API call fails, try to extract user info from email in token storage
          // This is a fallback for when API is not available
          const storedEmail = localStorage.getItem('exporter_email');
          if (storedEmail) {
            const userData: ExporterUser = {
              id: storedEmail,
              name: storedEmail.split('@')[0].replace(/[0-9]/g, '').replace(/([A-Z])/g, ' $1').trim() || 'Exporter',
              email: storedEmail,
              role: storedEmail.includes('admin') || storedEmail.includes('manager') ? 'tenant_admin' : 'exporter',
            };
            setUser(userData);
          } else {
            localStorage.removeItem('exporter_token');
            localStorage.removeItem('trdrhub_api_token');
          }
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('exporter_token');
        localStorage.removeItem('trdrhub_api_token');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      // Call real API for authentication
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();
      const apiToken = data.access_token;

      if (!apiToken) {
        throw new Error('No access token received');
      }

      // Store token in the format the API client expects
      localStorage.setItem('trdrhub_api_token', apiToken);
      localStorage.setItem('exporter_token', apiToken); // Keep for backward compatibility

      // Get user info from token or create user object
      // The API client will use the token for subsequent requests
      const userData: ExporterUser = {
        id: email, // Use email as ID for now
        name: email.split('@')[0].replace(/[0-9]/g, '').replace(/([A-Z])/g, ' $1').trim() || 'Exporter',
        email: email,
        role: email.includes('admin') || email.includes('manager') ? 'tenant_admin' : 'exporter',
      };

      // Store email for fallback auth check
      localStorage.setItem('exporter_email', email);

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
    localStorage.removeItem('trdrhub_api_token');
    localStorage.removeItem('exporter_email');
    setUser(null);
    navigate('/login'); // Redirect to main login page
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

