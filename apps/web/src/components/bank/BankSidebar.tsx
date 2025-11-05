import { Upload, Clock, CheckCircle, Users, Bell, BarChart3, Settings, HelpCircle, Building2 } from "lucide-react";
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
import { useAuth } from "@/hooks/use-auth";

const navMain = [
  {
    title: "Upload LC",
    url: "/lcopilot/bank-dashboard/v2?tab=upload",
    icon: Upload,
  },
  {
    title: "Processing Queue",
    url: "/lcopilot/bank-dashboard/v2?tab=queue",
    icon: Clock,
  },
  {
    title: "Results",
    url: "/lcopilot/bank-dashboard/v2?tab=results",
    icon: CheckCircle,
  },
  {
    title: "Clients",
    url: "/lcopilot/bank-dashboard/v2?tab=clients",
    icon: Users,
  },
  {
    title: "Analytics",
    url: "/lcopilot/bank-dashboard/v2?tab=analytics",
    icon: BarChart3,
  },
  {
    title: "Notifications",
    url: "/lcopilot/bank-dashboard/v2?tab=notifications",
    icon: Bell,
  },
];

const navSecondary = [
  {
    title: "Settings",
    url: "#",
    icon: Settings,
  },
  {
    title: "Help",
    url: "#",
    icon: HelpCircle,
  },
];

export function BankSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const location = useLocation();
  const { user } = useAuth();
  
  const isActive = (url: string) => {
    if (url === "#") return false;
    const urlParams = new URLSearchParams(url.split("?")[1]);
    const currentParams = new URLSearchParams(location.search);
    const urlTab = urlParams.get("tab");
    const currentTab = currentParams.get("tab") || "upload";
    return urlTab === currentTab;
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
        
        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              {navSecondary.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.title}>
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
              <SidebarMenuButton size="lg">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  {user.email?.charAt(0).toUpperCase() || "U"}
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="truncate font-medium text-sm">{user.email}</span>
                  <span className="text-xs text-muted-foreground capitalize">{user.role}</span>
                </div>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}

