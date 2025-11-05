// ImporterSidebar - Navigation component for Importer Dashboard
import { Upload, History, Bell, BarChart3, Settings, HelpCircle, Package } from "lucide-react";
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
import type { LucideIcon } from "lucide-react";

interface NavItem {
  title: string;
  url: string;
  icon?: LucideIcon;
}

const navMain: NavItem[] = [
  {
    title: "Dashboard",
    url: "/lcopilot/importer-dashboard",
    icon: BarChart3,
  },
  {
    title: "Upload LC",
    url: "/lcopilot/import-upload",
    icon: Upload,
  },
  {
    title: "Review Results",
    url: "/lcopilot/importer-dashboard?tab=results",
    icon: History,
  },
  {
    title: "Analytics",
    url: "/lcopilot/importer-analytics",
    icon: BarChart3,
  },
  {
    title: "Notifications",
    url: "/lcopilot/importer-dashboard?tab=notifications",
    icon: Bell,
  },
];

const navSecondary: NavItem[] = [
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

export function ImporterSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const location = useLocation();
  const { user } = useAuth();
  
  const isActive = (url: string) => {
    if (url === "#") return false;
    return location.pathname === url || location.pathname + location.search === url;
  };

  const mainItems = navMain.filter((item): item is NavItem => Boolean(item?.title && item?.url));
  const secondaryItems = navSecondary.filter((item): item is NavItem => Boolean(item?.title && item?.url));
  const isDev = typeof import.meta !== "undefined" ? !import.meta.env?.PROD : true;

  if (isDev && mainItems.length !== navMain.length) {
    console.warn("ImporterSidebar: filtered invalid main nav items", navMain);
  }
  if (isDev && secondaryItems.length !== navSecondary.length) {
    console.warn("ImporterSidebar: filtered invalid secondary nav items", navSecondary);
  }

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link to="/lcopilot">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-importer/10 text-importer">
                  <Package className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">LCopilot</span>
                  <span className="text-xs text-muted-foreground">Importer Portal</span>
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
              {mainItems.map((item) => {
                const Icon = item.icon ?? BarChart3;
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive(item.url)}
                      tooltip={item.title}
                    >
                      <Link to={item.url}>
                        <Icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              {secondaryItems.map((item) => {
                const Icon = item.icon ?? HelpCircle;
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild tooltip={item.title}>
                      <Link to={item.url}>
                        <Icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
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
