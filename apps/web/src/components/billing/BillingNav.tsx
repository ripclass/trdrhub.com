/**
 * BillingNav component - navigation tabs for billing dashboard
 */

import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  BarChart3,
  FileText,
  Activity,
  Settings,
  Download,
  RefreshCw,
  Crown,
  Building2
} from 'lucide-react';
// Inline cn function to avoid import/bundling issues
function cn(...classes: (string | undefined | null | boolean | Record<string, boolean>)[]): string {
  return classes
    .filter(Boolean)
    .map((cls) => {
      if (typeof cls === 'string') return cls;
      if (typeof cls === 'object' && cls !== null) {
        return Object.entries(cls)
          .filter(([_, val]) => val)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join(' ');
}
;
import { useAuth } from '@/hooks/useAuth';
import { RoleType } from '@/types/auth';

interface BillingNavProps {
  currentTab?: string;
  onTabChange?: (tab: string) => void;
  onUpgrade?: () => void;
  onRefresh?: () => void;
  onExport?: () => void;
  className?: string;
  showActions?: boolean;
  pendingInvoicesCount?: number;
  overdueInvoicesCount?: number;
}

export function BillingNav({
  currentTab,
  onTabChange,
  onUpgrade,
  onRefresh,
  onExport,
  className,
  showActions = true,
  pendingInvoicesCount = 0,
  overdueInvoicesCount = 0
}: BillingNavProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  // Determine current tab from route if not provided
  const activeTab = currentTab || (() => {
    const pathname = location.pathname;
    if (pathname.includes('/usage')) return 'usage';
    if (pathname.includes('/invoices')) return 'invoices';
    if (pathname.includes('/settings')) return 'settings';
    if (pathname.includes('/bank-compliance')) return 'bank-compliance';
    return 'overview';
  })();

  const handleTabChange = (tab: string) => {
    if (onTabChange) {
      onTabChange(tab);
    } else {
      // Default navigation behavior
      const basePath = location.pathname.includes('/admin/billing')
        ? '/dashboard/admin/billing'
        : '/dashboard/billing';

      switch (tab) {
        case 'overview':
          navigate(basePath);
          break;
        case 'usage':
          navigate(`${basePath}/usage`);
          break;
        case 'invoices':
          navigate(`${basePath}/invoices`);
          break;
        case 'settings':
          navigate(`${basePath}/settings`);
          break;
        case 'bank-compliance':
          navigate(`${basePath}/bank-compliance`);
          break;
        default:
          navigate(basePath);
      }
    }
  };

  const isAdmin = user?.role === RoleType.ADMIN;
  const isCompanyAdmin = user?.role === RoleType.COMPANY_ADMIN;
  const isBank = user?.role === RoleType.BANK;
  const canManageSettings = isAdmin || isCompanyAdmin;
  const canViewBankCompliance = isAdmin || isBank;

  return (
    <div className={cn('flex items-center justify-between', className)}>
      {/* Navigation tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className={`grid w-full lg:w-auto ${
          canViewBankCompliance && canManageSettings ? 'grid-cols-3 lg:grid-cols-5' :
          canViewBankCompliance || canManageSettings ? 'grid-cols-3 lg:grid-cols-4' :
          'grid-cols-3'
        }`}>
          <TabsTrigger value="overview" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            <span className="hidden sm:inline">Overview</span>
          </TabsTrigger>

          <TabsTrigger value="usage" className="gap-2">
            <Activity className="h-4 w-4" />
            <span className="hidden sm:inline">Usage</span>
          </TabsTrigger>

          <TabsTrigger value="invoices" className="gap-2 relative">
            <FileText className="h-4 w-4" />
            <span className="hidden sm:inline">Invoices</span>
            {(pendingInvoicesCount > 0 || overdueInvoicesCount > 0) && (
              <Badge
                variant={overdueInvoicesCount > 0 ? "destructive" : "secondary"}
                className="absolute -top-2 -right-2 h-5 w-5 p-0 flex items-center justify-center text-xs"
              >
                {overdueInvoicesCount > 0 ? overdueInvoicesCount : pendingInvoicesCount}
              </Badge>
            )}
          </TabsTrigger>

          {canViewBankCompliance && (
            <TabsTrigger value="bank-compliance" className="gap-2">
              <Building2 className="h-4 w-4" />
              <span className="hidden sm:inline">Bank Compliance</span>
            </TabsTrigger>
          )}

          {canManageSettings && (
            <TabsTrigger value="settings" className="gap-2">
              <Settings className="h-4 w-4" />
              <span className="hidden sm:inline">Settings</span>
            </TabsTrigger>
          )}
        </TabsList>
      </Tabs>

      {/* Action buttons */}
      {showActions && (
        <div className="flex items-center space-x-2">
          {/* Refresh button */}
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            <span className="hidden sm:inline">Refresh</span>
          </Button>

          {/* Export button */}
          {onExport && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExport}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              <span className="hidden sm:inline">Export</span>
            </Button>
          )}

          {/* Upgrade button */}
          {onUpgrade && (
            <Button
              size="sm"
              onClick={onUpgrade}
              className="gap-2"
            >
              <Crown className="h-4 w-4" />
              <span className="hidden sm:inline">Upgrade</span>
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

// Compact version for mobile
export function BillingNavMobile({
  currentTab,
  onTabChange,
  onUpgrade,
  className,
  pendingInvoicesCount = 0,
  overdueInvoicesCount = 0
}: BillingNavProps) {
  const location = useLocation();
  const navigate = useNavigate();

  const activeTab = currentTab || (() => {
    const pathname = location.pathname;
    if (pathname.includes('/usage')) return 'usage';
    if (pathname.includes('/invoices')) return 'invoices';
    return 'overview';
  })();

  const handleTabChange = (tab: string) => {
    if (onTabChange) {
      onTabChange(tab);
    } else {
      const basePath = '/dashboard/billing';
      switch (tab) {
        case 'overview':
          navigate(basePath);
          break;
        case 'usage':
          navigate(`${basePath}/usage`);
          break;
        case 'invoices':
          navigate(`${basePath}/invoices`);
          break;
        default:
          navigate(basePath);
      }
    }
  };

  return (
    <div className={cn('w-full', className)}>
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="grid grid-cols-3 w-full">
          <TabsTrigger value="overview" className="flex flex-col gap-1 py-3">
            <BarChart3 className="h-4 w-4" />
            <span className="text-xs">Overview</span>
          </TabsTrigger>

          <TabsTrigger value="usage" className="flex flex-col gap-1 py-3">
            <Activity className="h-4 w-4" />
            <span className="text-xs">Usage</span>
          </TabsTrigger>

          <TabsTrigger value="invoices" className="flex flex-col gap-1 py-3 relative">
            <FileText className="h-4 w-4" />
            <span className="text-xs">Invoices</span>
            {(pendingInvoicesCount > 0 || overdueInvoicesCount > 0) && (
              <Badge
                variant={overdueInvoicesCount > 0 ? "destructive" : "secondary"}
                className="absolute -top-1 -right-1 h-4 w-4 p-0 flex items-center justify-center text-xs"
              >
                {overdueInvoicesCount > 0 ? overdueInvoicesCount : pendingInvoicesCount}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Mobile upgrade button */}
      {onUpgrade && (
        <div className="mt-3">
          <Button
            size="sm"
            onClick={onUpgrade}
            className="w-full gap-2"
          >
            <Crown className="h-4 w-4" />
            Upgrade Plan
          </Button>
        </div>
      )}
    </div>
  );
}

// Breadcrumb component for billing pages
interface BillingBreadcrumbProps {
  items?: Array<{
    label: string;
    href?: string;
    active?: boolean;
  }>;
  className?: string;
}

export function BillingBreadcrumb({ items, className }: BillingBreadcrumbProps) {
  const location = useLocation();
  const navigate = useNavigate();

  // Default breadcrumb items based on current route
  const defaultItems = (() => {
    const pathname = location.pathname;
    const basePath = pathname.includes('/admin/billing') ? 'Admin' : 'Dashboard';

    const breadcrumbs: Array<{
      label: string;
      href?: string;
      active?: boolean;
    }> = [
      { label: basePath, href: basePath === 'Admin' ? '/dashboard/admin' : '/dashboard' },
      { label: 'Billing', href: basePath === 'Admin' ? '/dashboard/admin/billing' : '/dashboard/billing' }
    ];

    if (pathname.includes('/usage')) {
      breadcrumbs.push({ label: 'Usage', active: true });
    } else if (pathname.includes('/invoices')) {
      breadcrumbs.push({ label: 'Invoices', active: true });
    } else if (pathname.includes('/settings')) {
      breadcrumbs.push({ label: 'Settings', active: true });
    } else if (pathname.includes('/bank-compliance')) {
      breadcrumbs.push({ label: 'Bank Compliance', active: true });
    }

    return breadcrumbs;
  })();

  const breadcrumbItems = items || defaultItems;

  return (
    <nav className={cn('flex items-center space-x-1 text-sm', className)}>
      {breadcrumbItems.map((item, index) => (
        <React.Fragment key={index}>
          {index > 0 && <span className="text-muted-foreground">/</span>}
          {item.active ? (
            <span className="font-medium">{item.label}</span>
          ) : (
            <button
              onClick={() => item.href && navigate(item.href)}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {item.label}
            </button>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}