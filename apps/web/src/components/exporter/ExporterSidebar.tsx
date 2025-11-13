// ExporterSidebar - Navigation component for Exporter Dashboard
import { Upload, Clock, Bell, BarChart3, Settings, HelpCircle, Building2, FolderKanban, FileText, CreditCard, Sparkles, Library, Calendar, LogOut } from "lucide-react";
import { useLocation } from "react-router-dom";
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
import { useExporterAuth } from "@/lib/exporter/auth";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";

type ExporterSection =
  | "dashboard"
  | "workspace"
  | "templates"
  | "upload"
  | "reviews"
  | "analytics"
  | "notifications"
  | "billing"
  | "ai-assistance"
  | "content-library"
  | "shipment-timeline"
  | "settings"
  | "help";

interface ExporterSidebarProps extends React.ComponentProps<typeof Sidebar> {
  activeSection: ExporterSection;
  onSectionChange: (section: ExporterSection) => void;
  user?: { name?: string; email?: string; id?: string; role?: string };
}

export function ExporterSidebar({ activeSection, onSectionChange, user: propUser, ...props }: ExporterSidebarProps) {
  const location = useLocation();
  const { user: exporterAuthUser, logout: exporterLogout } = useExporterAuth();
  const { logout: mainLogout } = useAuth();
  
  // Use propUser if provided (from main auth), otherwise fall back to exporterAuthUser
  const user = propUser || exporterAuthUser;
  
  const isActive = (url: string) => {
    if (url === "#") return false;
    return location.pathname === url || location.pathname + location.search === url;
  };

  const handleLogout = async () => {
    // Logout from both auth systems
    try {
      await mainLogout();
    } catch (error) {
      console.warn('Main auth logout failed:', error);
    }
    exporterLogout(); // This will navigate to /login
  };

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <div className="flex items-center gap-3">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-exporter/10 text-exporter">
                  <Building2 className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">LCopilot</span>
                  <span className="text-xs text-muted-foreground">Exporter Portal</span>
                </div>
              </div>
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
                <SidebarMenuButton
                  isActive={activeSection === "dashboard"}
                  onClick={() => onSectionChange("dashboard")}
                >
                  <BarChart3 />
                  <span>Dashboard</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "templates"}
                  onClick={() => onSectionChange("templates")}
                  tooltip="Templates"
                >
                  <FileText />
                  <span>Templates</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "upload"}
                  onClick={() => onSectionChange("upload")}
                  tooltip="Upload Documents"
                >
                  <Upload />
                  <span>Upload Documents</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "reviews"}
                  onClick={() => onSectionChange("reviews")}
                  tooltip="Review Results"
                >
                  <Clock />
                  <span>Review Results</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "workspace"}
                  onClick={() => onSectionChange("workspace")}
                  tooltip="LC Workspace"
                >
                  <FolderKanban />
                  <span>LC Workspace</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "analytics"}
                  onClick={() => onSectionChange("analytics")}
                  tooltip="Analytics"
                >
                  <BarChart3 />
                  <span>Analytics</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "notifications"}
                  onClick={() => onSectionChange("notifications")}
                  tooltip="Notifications"
                >
                  <Bell />
                  <span>Notifications</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup>
          <SidebarGroupLabel>Billing & Finance</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "billing"}
                  onClick={() => onSectionChange("billing")}
                  tooltip="Billing"
                >
                  <CreditCard />
                  <span>Billing</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup>
          <SidebarGroupLabel>AI & Tools</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "ai-assistance"}
                  onClick={() => onSectionChange("ai-assistance")}
                  tooltip="AI Assistance"
                >
                  <Sparkles />
                  <span>AI Assistance</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "content-library"}
                  onClick={() => onSectionChange("content-library")}
                  tooltip="Content Library"
                >
                  <Library />
                  <span>Content Library</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "shipment-timeline"}
                  onClick={() => onSectionChange("shipment-timeline")}
                  tooltip="Shipment Timeline"
                >
                  <Calendar />
                  <span>Shipment Timeline</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "settings" || isActive("/lcopilot/exporter-dashboard?tab=settings")}
                  onClick={() => onSectionChange("settings")}
                  tooltip="Settings"
                >
                  <Settings />
                  <span>Settings</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "help"}
                  onClick={() => onSectionChange("help")}
                  tooltip="Help"
                >
                  <HelpCircle />
                  <span>Help</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
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
                  <span className="text-xs text-muted-foreground capitalize">{user.role === 'tenant_admin' ? 'Admin' : 'Exporter'}</span>
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
