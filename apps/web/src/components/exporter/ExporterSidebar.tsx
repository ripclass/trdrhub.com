// ExporterSidebar - Navigation component for Exporter Dashboard
import { Upload, Clock, Bell, BarChart3, Settings, HelpCircle, Building2, FolderKanban, FileText } from "lucide-react";
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
import { useAuth } from "@/hooks/use-auth";

type ExporterSection =
  | "dashboard"
  | "workspace"
  | "templates"
  | "upload"
  | "reviews"
  | "analytics"
  | "notifications"
  | "settings"
  | "help";

interface ExporterSidebarProps extends React.ComponentProps<typeof Sidebar> {
  activeSection: ExporterSection;
  onSectionChange: (section: ExporterSection) => void;
}

export function ExporterSidebar({ activeSection, onSectionChange, ...props }: ExporterSidebarProps) {
  const location = useLocation();
  const { user } = useAuth();
  
  const isActive = (url: string) => {
    if (url === "#") return false;
    return location.pathname === url || location.pathname + location.search === url;
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
