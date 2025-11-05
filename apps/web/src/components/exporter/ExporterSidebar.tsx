// ExporterSidebar - Navigation component for Exporter Dashboard
import { Upload, Clock, Bell, BarChart3, Settings, HelpCircle, Building2 } from "lucide-react";
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

export function ExporterSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const location = useLocation();
  const { user } = useAuth();
  
  const isActive = (url: string) => {
    if (url === "#") return false;
    return location.pathname === url || location.pathname + location.search === url;
  };

  const secondaryLinks = (
    <>
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip="Settings" isActive={isActive("/lcopilot/exporter-dashboard?tab=settings")}>
          <Link to="/lcopilot/exporter-dashboard?tab=settings">
            <Settings />
            <span>Settings</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip="Help">
          <Link to="/help">
            <HelpCircle />
            <span>Help</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </>
  );

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link to="/lcopilot">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-exporter/10 text-exporter">
                  <Building2 className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">LCopilot</span>
                  <span className="text-xs text-muted-foreground">Exporter Portal</span>
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
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="Dashboard" isActive={isActive("/lcopilot/exporter-dashboard")}>
                  <Link to="/lcopilot/exporter-dashboard">
                    <BarChart3 />
                    <span>Dashboard</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="Upload Documents" isActive={isActive("/export-lc-upload")}>
                  <Link to="/export-lc-upload">
                    <Upload />
                    <span>Upload Documents</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="Review Results" isActive={isActive("/lcopilot/exporter-results")}>
                  <Link to="/lcopilot/exporter-results">
                    <Clock />
                    <span>Review Results</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="Analytics" isActive={isActive("/lcopilot/exporter-analytics")}>
                  <Link to="/lcopilot/exporter-analytics">
                    <BarChart3 />
                    <span>Analytics</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="Notifications" isActive={isActive("/lcopilot/exporter-dashboard?tab=notifications")}>
                  <Link to="/lcopilot/exporter-dashboard?tab=notifications">
                    <Bell />
                    <span>Notifications</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>{secondaryLinks}</SidebarMenu>
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
