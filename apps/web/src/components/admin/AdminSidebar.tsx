import React from 'react';
import { useLocation } from 'react-router-dom';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
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

type AdminSection =
  | "overview"
  | "ops-monitoring"
  | "ops-jobs"
  | "ops-alerts"
  | "audit-logs"
  | "audit-approvals"
  | "audit-compliance"
  | "security-users"
  | "security-access"
  | "security-sessions"
  | "billing-plans"
  | "billing-adjustments"
  | "billing-disputes"
  | "partners-registry"
  | "partners-connectors"
  | "partners-webhooks"
  | "llm-prompts"
  | "llm-budgets"
  | "llm-evaluations"
  | "compliance-residency"
  | "compliance-retention"
  | "compliance-legal-holds"
  | "system-feature-flags"
  | "system-releases"
  | "system-settings";

interface AdminSidebarProps extends React.ComponentProps<typeof Sidebar> {
  activeSection: AdminSection;
  onSectionChange: (section: AdminSection) => void;
}

interface SidebarSection {
  title: string;
  items: SidebarItem[];
}

interface SidebarItem {
  name: string;
  section: AdminSection;
  icon: React.ComponentType<{ className?: string }>;
  permissions?: string[];
  badge?: string;
}

const navigation: SidebarSection[] = [
  {
    title: 'Overview',
    items: [
      { name: 'Dashboard', section: 'overview', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Operations',
    items: [
      { name: 'Monitoring', section: 'ops-monitoring', icon: Activity, permissions: ['ops:read'] },
      { name: 'Jobs & Queue', section: 'ops-jobs', icon: Zap, permissions: ['jobs:read'] },
      { name: 'Alerts', section: 'ops-alerts', icon: AlertTriangle, permissions: ['ops:read'], badge: '2' },
    ],
  },
  {
    title: 'Audit & Governance',
    items: [
      { name: 'Audit Logs', section: 'audit-logs', icon: Search, permissions: ['audit:read'] },
      { name: 'Approvals', section: 'audit-approvals', icon: CheckSquare, permissions: ['approvals:read'], badge: '3' },
      { name: 'Compliance', section: 'audit-compliance', icon: Shield, permissions: ['compliance:read'] },
    ],
  },
  {
    title: 'Security & Access',
    items: [
      { name: 'Users & Tenants', section: 'security-users', icon: Users, permissions: ['users:read'] },
      { name: 'API Keys', section: 'security-access', icon: Lock, permissions: ['api_keys:read'] },
      { name: 'Sessions', section: 'security-sessions', icon: Clock, permissions: ['sessions:read'] },
    ],
  },
  {
    title: 'Billing & Finance',
    items: [
      { name: 'Plans & Pricing', section: 'billing-plans', icon: CreditCard, permissions: ['billing:read'] },
      { name: 'Adjustments', section: 'billing-adjustments', icon: DollarSign, permissions: ['billing:read'] },
      { name: 'Disputes', section: 'billing-disputes', icon: AlertTriangle, permissions: ['disputes:read'] },
    ],
  },
  {
    title: 'Partners & Integration',
    items: [
      { name: 'Partner Registry', section: 'partners-registry', icon: Building, permissions: ['partners:read'] },
      { name: 'Connectors', section: 'partners-connectors', icon: Webhook, permissions: ['partners:read'] },
      { name: 'Webhooks', section: 'partners-webhooks', icon: Globe, permissions: ['webhooks:read'] },
    ],
  },
  {
    title: 'LLM Operations',
    items: [
      { name: 'Prompts', section: 'llm-prompts', icon: Brain, permissions: ['llm:read'] },
      { name: 'Budgets', section: 'llm-budgets', icon: BarChart3, permissions: ['llm:read'] },
      { name: 'Evaluations', section: 'llm-evaluations', icon: TestTube, permissions: ['llm:read'] },
    ],
  },
  {
    title: 'Compliance & Data',
    items: [
      { name: 'Data Residency', section: 'compliance-residency', icon: Globe, permissions: ['compliance:read'] },
      { name: 'Retention', section: 'compliance-retention', icon: Database, permissions: ['compliance:read'] },
      { name: 'Legal Holds', section: 'compliance-legal-holds', icon: Folder, permissions: ['legal_holds:read'] },
    ],
  },
  {
    title: 'System',
    items: [
      { name: 'Feature Flags', section: 'system-feature-flags', icon: Flag, permissions: ['feature_flags:read'] },
      { name: 'Releases', section: 'system-releases', icon: FileText, permissions: ['releases:read'] },
      { name: 'Settings', section: 'system-settings', icon: Settings, permissions: ['settings:read'] },
    ],
  },
];

export function AdminSidebar({ activeSection, onSectionChange, ...props }: AdminSidebarProps) {
  const location = useLocation();
  const { permissions, user } = useAdminAuth();

  const hasPermission = (requiredPermissions?: string[]) => {
    if (!requiredPermissions) return true;
    if (permissions.includes('*')) return true;
    return requiredPermissions.some(permission => permissions.includes(permission));
  };

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <div className="flex items-center gap-3">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-blue-600 text-white">
                  <Shield className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">Admin Console</span>
                  <span className="text-xs text-muted-foreground">System Administration</span>
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {navigation.map((section) => (
          <SidebarGroup key={section.title}>
            <SidebarGroupLabel>{section.title}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {section.items
                  .filter(item => hasPermission(item.permissions))
                  .map((item) => (
                    <SidebarMenuItem key={item.section}>
                      <SidebarMenuButton
                        isActive={activeSection === item.section}
                        onClick={() => onSectionChange(item.section)}
                        tooltip={item.name}
                      >
                        <item.icon />
                        <span>{item.name}</span>
                        {item.badge && (
                          <span className="ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-destructive/10 text-destructive">
                            {item.badge}
                          </span>
                        )}
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        {user && (
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  {user.email?.charAt(0).toUpperCase() || user.name?.charAt(0).toUpperCase() || "A"}
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="truncate font-medium text-sm">{user.name || user.email}</span>
                  <span className="text-xs text-muted-foreground capitalize">{user.role?.replace('_', ' ')}</span>
                </div>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}