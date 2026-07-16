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
  Folder,
  Receipt,
  TrendingUp,
  Calculator,
  BookOpen,
  Settings2,
  Landmark,
  UserPlus,
} from 'lucide-react';
import { useAdminAuth } from '@/lib/admin/auth';
import { UserMenu } from '@/components/layout/UserMenu';

type AdminSection =
  | "overview"
  | "review-queue"
  | "proofline-review"
  | "ops-monitoring"
  | "ops-jobs"
  | "ops-alerts"
  | "audit-logs"
  | "audit-approvals"
  | "audit-compliance"
  | "security-users"
  | "security-access"
  | "security-sessions"
  | "banks-management"
  | "billing-overview"
  | "billing-invoices-payments"
  | "billing-recognition"
  | "billing-taxes"
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
  | "system-settings"
  | "rules-list"
  | "rules-upload"
  | "rules-active"
  | "rules-governance";

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

// Launch sidebar (2026-07-07 audit): only sections with WORKING backends.
// The parked groups below queried tables that were never migrated to prod
// (job_queue, audit_events, admin_alerts, ...) or threw client-side
// "Not implemented" — they 500'd or rendered empty scaffolding. Restore a
// group only after its backend is real and live-verified. Full list of
// parked sections preserved in git history (this file, pre-2026-07-07).
const navigation: SidebarSection[] = [
  {
    title: 'Overview',
    items: [
      { name: 'Dashboard', section: 'overview', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Concierge',
    items: [
      // Backend enforces require_sysadmin; sysadmins carry the '*' permission.
      { name: 'Review Queue', section: 'review-queue', icon: CheckSquare, permissions: ['review:read'] },
      { name: 'Proofline Queue', section: 'proofline-review', icon: Shield, permissions: ['review:read'] },
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
          <UserMenu variant="sidebar" />
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
