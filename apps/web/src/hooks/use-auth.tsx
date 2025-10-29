import * as React from "react";
import type { Role } from "@/types/analytics";

export interface User {
  id: number;
  email: string;
  username?: string;
  role: Role;
  isActive: boolean;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (role: Role | Role[]) => boolean;
}

const AuthContext = React.createContext<AuthContextType | null>(null);

// Mock user for development - in real app this would come from your auth system
const mockUser: User = {
  id: 1,
  email: "demo@lcopilot.com",
  username: "Demo User",
  role: "exporter", // Change this to test different roles: "exporter" | "importer" | "bank" | "admin"
  isActive: true,
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(mockUser);
  const [isLoading, setIsLoading] = React.useState(false);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      // In real app, make API call to authenticate
      // For now, just set mock user
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      setUser(mockUser);
    } catch (error) {
      throw new Error("Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
  };

  const hasRole = (role: Role | Role[]) => {
    if (!user) return false;
    if (Array.isArray(role)) {
      return role.includes(user.role);
    }
    return user.role === role;
  };

  const value = { user, isLoading, login, logout, hasRole };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}