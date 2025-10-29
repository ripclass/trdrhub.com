import React from 'react';
import { Navigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Shield, AlertTriangle, Lock } from 'lucide-react';
import { useAdminAuth } from '@/lib/admin/auth';
import { Skeleton } from '@/components/ui/skeleton';

interface AdminRouteProps {
  children: React.ReactNode;
  requiredPermissions?: string[];
  fallback?: React.ReactNode;
}

function AdminAccessDenied({ requiredPermissions }: { requiredPermissions: string[] }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <Lock className="w-6 h-6 text-red-600" />
          </div>
          <CardTitle className="text-xl">Access Denied</CardTitle>
          <CardDescription>
            You don't have permission to access this area of the admin console.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-gray-50 p-3 rounded-lg">
            <p className="text-sm font-medium text-gray-900 mb-2">
              Required Permissions:
            </p>
            <ul className="text-xs text-gray-600 space-y-1">
              {requiredPermissions.map((permission) => (
                <li key={permission} className="flex items-center gap-2">
                  <Shield className="w-3 h-3" />
                  {permission}
                </li>
              ))}
            </ul>
          </div>
          <div className="text-center">
            <Button
              variant="outline"
              onClick={() => window.history.back()}
              className="mr-2"
            >
              Go Back
            </Button>
            <Button asChild>
              <a href="/admin">Admin Dashboard</a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AdminLoginPrompt() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
            <Shield className="w-6 h-6 text-blue-600" />
          </div>
          <CardTitle className="text-xl">Admin Access Required</CardTitle>
          <CardDescription>
            Please sign in with your admin credentials to access the admin console.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-yellow-50 border border-yellow-200 p-3 rounded-lg flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-yellow-800">
              <p className="font-medium">Admin Console</p>
              <p className="mt-1">
                This area requires special administrative privileges.
                Contact your system administrator if you need access.
              </p>
            </div>
          </div>
          <div className="text-center">
            <Button asChild className="w-full">
              <a href="/admin/login">Sign In as Admin</a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AdminLoadingScreen() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header Skeleton */}
      <div className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
        <Skeleton className="h-8 w-64" />
        <div className="flex items-center gap-4">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-8 w-8 rounded-full" />
        </div>
      </div>

      <div className="flex h-[calc(100vh-64px)]">
        {/* Sidebar Skeleton */}
        <div className="w-64 bg-white border-r border-gray-200 p-6">
          <Skeleton className="h-8 w-32 mb-6" />
          <div className="space-y-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-16" />
                <div className="space-y-1 ml-4">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Main Content Skeleton */}
        <div className="flex-1 p-8">
          <div className="space-y-6">
            <div>
              <Skeleton className="h-8 w-64 mb-2" />
              <Skeleton className="h-4 w-96" />
            </div>
            <div className="grid grid-cols-4 gap-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-white p-6 rounded-lg border">
                  <Skeleton className="h-4 w-16 mb-2" />
                  <Skeleton className="h-8 w-20 mb-1" />
                  <Skeleton className="h-3 w-12" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function AdminRoute({
  children,
  requiredPermissions = [],
  fallback
}: AdminRouteProps) {
  const { user, permissions, isLoading, isAuthenticated } = useAdminAuth();

  // Show loading screen while checking authentication
  if (isLoading) {
    return <AdminLoadingScreen />;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    return <AdminLoginPrompt />;
  }

  // Check permissions if required
  if (requiredPermissions.length > 0) {
    const hasPermission = requiredPermissions.every(
      permission => permissions.includes(permission) || permissions.includes('*')
    );

    if (!hasPermission) {
      return fallback || <AdminAccessDenied requiredPermissions={requiredPermissions} />;
    }
  }

  return <>{children}</>;
}