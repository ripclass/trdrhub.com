import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Activity,
  Settings,
  Users,
  Shield,
  DollarSign,
  Building,
  Brain,
  Database,
  Flag,
  FileText,
  Search,
  CheckSquare,
  Zap,
  BarChart3,
  Clock,
  AlertTriangle,
  Globe,
  Lock,
  CreditCard,
  Webhook,
  TestTube,
  Folder
} from 'lucide-react';
import { useAdminAuth } from '@/lib/admin/auth';

interface SidebarSection {
  title: string;
  items: SidebarItem[];
}

interface SidebarItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  permissions?: string[];
  badge?: string;
}

const navigation: SidebarSection[] = [
  {
    title: 'Overview',
    items: [
      { name: 'Dashboard', href: '/admin', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Operations',
    items: [
      { name: 'Monitoring', href: '/admin/ops/monitoring', icon: Activity, permissions: ['ops:read'] },
      { name: 'Jobs & Queue', href: '/admin/ops/jobs', icon: Zap, permissions: ['jobs:read'] },
      { name: 'Alerts', href: '/admin/ops/alerts', icon: AlertTriangle, permissions: ['ops:read'], badge: '2' },
    ],
  },
  {
    title: 'Audit & Governance',
    items: [
      { name: 'Audit Logs', href: '/admin/audit/logs', icon: Search, permissions: ['audit:read'] },
      { name: 'Approvals', href: '/admin/audit/approvals', icon: CheckSquare, permissions: ['approvals:read'], badge: '3' },
      { name: 'Compliance', href: '/admin/audit/compliance', icon: Shield, permissions: ['compliance:read'] },
    ],
  },
  {
    title: 'Security & Access',
    items: [
      { name: 'Users & Tenants', href: '/admin/security/users', icon: Users, permissions: ['users:read'] },
      { name: 'API Keys', href: '/admin/security/access', icon: Lock, permissions: ['api_keys:read'] },
      { name: 'Sessions', href: '/admin/security/sessions', icon: Clock, permissions: ['sessions:read'] },
    ],
  },
  {
    title: 'Billing & Finance',
    items: [
      { name: 'Plans & Pricing', href: '/admin/billing/plans', icon: CreditCard, permissions: ['billing:read'] },
      { name: 'Adjustments', href: '/admin/billing/adjustments', icon: DollarSign, permissions: ['billing:read'] },
      { name: 'Disputes', href: '/admin/billing/disputes', icon: AlertTriangle, permissions: ['disputes:read'] },
    ],
  },
  {
    title: 'Partners & Integration',
    items: [
      { name: 'Partner Registry', href: '/admin/partners/registry', icon: Building, permissions: ['partners:read'] },
      { name: 'Connectors', href: '/admin/partners/connectors', icon: Webhook, permissions: ['partners:read'] },
      { name: 'Webhooks', href: '/admin/partners/webhooks', icon: Globe, permissions: ['webhooks:read'] },
    ],
  },
  {
    title: 'LLM Operations',
    items: [
      { name: 'Prompts', href: '/admin/llm/prompts', icon: Brain, permissions: ['llm:read'] },
      { name: 'Budgets', href: '/admin/llm/budgets', icon: BarChart3, permissions: ['llm:read'] },
      { name: 'Evaluations', href: '/admin/llm/evaluations', icon: TestTube, permissions: ['llm:read'] },
    ],
  },
  {
    title: 'Compliance & Data',
    items: [
      { name: 'Data Residency', href: '/admin/compliance/residency', icon: Globe, permissions: ['compliance:read'] },
      { name: 'Retention', href: '/admin/compliance/retention', icon: Database, permissions: ['compliance:read'] },
      { name: 'Legal Holds', href: '/admin/compliance/legal-holds', icon: Folder, permissions: ['legal_holds:read'] },
    ],
  },
  {
    title: 'System',
    items: [
      { name: 'Feature Flags', href: '/admin/system/feature-flags', icon: Flag, permissions: ['feature_flags:read'] },
      { name: 'Releases', href: '/admin/system/releases', icon: FileText, permissions: ['releases:read'] },
      { name: 'Settings', href: '/admin/system/settings', icon: Settings, permissions: ['settings:read'] },
    ],
  },
];

export function AdminSidebar() {
  const { pathname } = useLocation();
  const { permissions } = useAdminAuth();

  const hasPermission = (requiredPermissions?: string[]) => {
    if (!requiredPermissions) return true;
    if (permissions.includes('*')) return true;
    return requiredPermissions.some(permission => permissions.includes(permission));
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 overflow-y-auto">
      <div className="p-6">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">LC</span>
          </div>
          <span className="font-bold text-gray-900">Admin Console</span>
        </div>
      </div>

      <nav className="px-4 pb-4">
        {navigation.map((section) => (
          <div key={section.title} className="mb-6">
            <h3 className="px-2 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              {section.title}
            </h3>
            <ul className="space-y-1">
              {section.items
                .filter(item => hasPermission(item.permissions))
                .map((item) => {
                  const isActive = pathname === item.href;
                  return (
                    <li key={item.name}>
                      <Link
                        to={item.href}
                        className={cn(
                          'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors',
                          isActive
                            ? 'bg-blue-100 text-blue-700'
                            : 'text-gray-700 hover:text-gray-900 hover:bg-gray-50'
                        )}
                      >
                        <item.icon
                          className={cn(
                            'mr-3 h-5 w-5 flex-shrink-0',
                            isActive
                              ? 'text-blue-500'
                              : 'text-gray-400 group-hover:text-gray-500'
                          )}
                        />
                        <span className="flex-1">{item.name}</span>
                        {item.badge && (
                          <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            {item.badge}
                          </span>
                        )}
                      </Link>
                    </li>
                  );
                })}
            </ul>
          </div>
        ))}
      </nav>
    </div>
  );
}