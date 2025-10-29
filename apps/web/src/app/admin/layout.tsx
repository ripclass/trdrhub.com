import React from 'react';
import { AdminSidebar } from '@/components/admin/AdminSidebar';
import { AdminHeader } from '@/components/admin/AdminHeader';
import { AdminRoute } from '@/components/admin/AdminRoute';

interface AdminLayoutProps {
  children: React.ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <AdminRoute>
      <div className="min-h-screen bg-gray-50">
        <AdminHeader />
        <div className="flex h-[calc(100vh-64px)]">
          <AdminSidebar />
          <main className="flex-1 overflow-auto">
            <div className="container mx-auto px-6 py-8">
              {children}
            </div>
          </main>
        </div>
      </div>
    </AdminRoute>
  );
}