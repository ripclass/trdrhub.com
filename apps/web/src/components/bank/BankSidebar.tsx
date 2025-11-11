import { Upload, Clock, CheckCircle, Users, Bell, BarChart3, Settings, HelpCircle, Building2, FileCheck, AlertTriangle, Shield, Gauge, Package, LayoutDashboard, CreditCard, Sparkles, UserCog, LogOut, FolderKanban, Plug } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
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
import { useBankAuth } from "@/lib/bank/auth";
import { Button } from "@/components/ui/button";

const navMain = [
  {
    title: "Dashboard",
    url: "/lcopilot/bank-dashboard?tab=dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "Upload LC",
    url: "/lcopilot/bank-dashboard?tab=upload",
    icon: Upload,
  },
  {
    title: "Processing Queue",
    url: "/lcopilot/bank-dashboard?tab=queue",
    icon: Clock,
  },
  {
    title: "Results",
    url: "/lcopilot/bank-dashboard?tab=results",
    icon: CheckCircle,
  },
  {
    title: "Clients",
    url: "/lcopilot/bank-dashboard?tab=clients",
    icon: Users,
  },
  {
    title: "Notifications",
    url: "/lcopilot/bank-dashboard?tab=notifications",
    icon: Bell,
  },
];

const navAnalytics = [
  {
    title: "Analytics",
    url: "/lcopilot/bank-dashboard?tab=analytics",
    icon: BarChart3,
  },
  {
    title: "SLA Dashboards",
    url: "/lcopilot/bank-dashboard?tab=sla",
    icon: Gauge,
  },
];

const navOperations = [
  {
    title: "Approvals",
    url: "/lcopilot/bank-dashboard?tab=approvals",
    icon: FileCheck,
  },
  {
    title: "Discrepancies",
    url: "/lcopilot/bank-dashboard?tab=discrepancies",
    icon: AlertTriangle,
  },
  {
    title: "Policy",
    url: "/lcopilot/bank-dashboard?tab=policy",
    icon: Shield,
  },
  {
    title: "Evidence Packs",
    url: "/lcopilot/bank-dashboard?tab=evidence-packs",
    icon: Package,
  },
  {
    title: "Bulk Jobs",
    url: "/lcopilot/bank-dashboard?tab=bulk-jobs",
    icon: FolderKanban,
  },
];

const navBilling = [
  {
    title: "Billing",
    url: "/lcopilot/bank-dashboard?tab=billing",
    icon: CreditCard,
  },
];

const navAITools = [
  {
    title: "AI Assistance",
    url: "/lcopilot/bank-dashboard?tab=ai-assistance",
    icon: Sparkles,
  },
  {
    title: "Integrations",
    url: "/lcopilot/bank-dashboard?tab=integrations",
    icon: Plug,
  },
];

const navSecondary = [
  {
    title: "Users",
    url: "/lcopilot/bank-dashboard?tab=users",
    icon: UserCog,
  },
  {
    title: "Settings",
    url: "/lcopilot/bank-dashboard?tab=settings",
    icon: Settings,
  },
  {
    title: "Help",
    url: "/lcopilot/bank-dashboard?tab=help",
    icon: HelpCircle,
  },
];

export function BankSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const location = useLocation();
  const { user, logout } = useBankAuth();
  const isBankAdmin = user?.role === 'bank_admin';
  
  const isActive = (url: string) => {
    if (url === "#") return false;
    const urlParams = new URLSearchParams(url.split("?")[1] || "");
    const currentParams = new URLSearchParams(location.search);
    const urlTab = urlParams.get("tab");
    const currentTab = currentParams.get("tab") || "dashboard";
    return urlTab === currentTab;
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link to="/lcopilot">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Building2 className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">LCopilot</span>
                  <span className="text-xs text-muted-foreground">Bank Portal</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Main Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navMain.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.url)}
                    tooltip={item.title}
                  >
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup>
          <SidebarGroupLabel>Analytics & Reporting</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navAnalytics.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.url)}
                    tooltip={item.title}
                  >
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup>
          <SidebarGroupLabel>Operations</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navOperations.filter(item => item.title !== 'Policy' || isBankAdmin).map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.url)}
                    tooltip={item.title}
                  >
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup>
          <SidebarGroupLabel>Billing & Finance</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navBilling.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.url)}
                    tooltip={item.title}
                  >
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup>
          <SidebarGroupLabel>AI & Tools</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navAITools.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.url)}
                    tooltip={item.title}
                  >
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              {navSecondary.filter(item => item.title !== 'Users' || isBankAdmin).map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.title} isActive={isActive(item.url)}>
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      
      <SidebarFooter>
        {user && (
          <SidebarMenu>
            <SidebarMenuItem>
              <div className="flex items-center gap-2 px-2 py-1.5 w-full">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  {user.name?.charAt(0).toUpperCase() || user.email?.charAt(0).toUpperCase() || "U"}
                </div>
                <div className="flex flex-col gap-0.5 leading-none flex-1 min-w-0">
                  <span className="truncate font-medium text-sm">{user.name || user.email}</span>
                  <span className="text-xs text-muted-foreground">{user.role === 'bank_admin' ? 'Bank Admin' : 'Bank Officer'}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  className="h-8 w-8 p-0"
                  title="Sign out"
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            </SidebarMenuItem>
          </SidebarMenu>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}

