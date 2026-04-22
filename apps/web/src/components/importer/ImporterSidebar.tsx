// ImporterSidebar — Phase 4/2 rewrite.
//
// Slimmed from 14 items to a 5-item minimum that matches the exporter
// skeleton shape:
//   Dashboard · Draft LC Review · Supplier Doc Review · Billing · Settings
//
// Dropped items (reachable elsewhere):
//   * Workspace / Templates / Analytics / Notifications / AI Assistance /
//     Content Library / Shipment Timeline — folded into the dashboard
//     recent-activity + stats surfaces per Phase 4/4
//   * Help → moved to top-bar (future polish)
//   * Legacy routes still resolve via the ?section= redirect layer in
//     Phase 4/6, so bookmarks keep working.
import {
  BarChart3,
  FileText,
  ShieldCheck,
  Settings,
  Building2,
  CreditCard,
  LogOut,
  ArrowLeft,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";

export type ImporterSidebarSection =
  | "dashboard"
  | "draft-lc"
  | "supplier-docs"
  | "billing"
  | "settings";

interface ImporterSidebarProps extends React.ComponentProps<typeof Sidebar> {
  activeSection: ImporterSidebarSection;
  onSectionChange: (section: ImporterSidebarSection) => void;
  user?: { name?: string; email?: string; id?: string; role?: string };
}

export function ImporterSidebar({
  activeSection,
  onSectionChange,
  user: propUser,
  ...props
}: ImporterSidebarProps) {
  const { user: authUser, logout } = useAuth();
  const user = propUser || authUser;
  const displayName =
    propUser?.name || authUser?.full_name || authUser?.username || user?.email;

  const handleLogout = async (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    await logout();
  };

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <div className="px-2 pt-2">
          <Link
            to="/hub"
            className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors mb-2"
          >
            <ArrowLeft className="h-3 w-3" />
            Back to Hub
          </Link>
        </div>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <div className="flex items-center gap-3">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-importer/10 text-importer">
                  <Building2 className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">LCopilot</span>
                  <span className="text-xs text-muted-foreground">
                    Importer Portal
                  </span>
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "dashboard"}
                  onClick={() => onSectionChange("dashboard")}
                  tooltip="Dashboard"
                >
                  <BarChart3 />
                  <span>Dashboard</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "draft-lc"}
                  onClick={() => onSectionChange("draft-lc")}
                  tooltip="Draft LC Review"
                >
                  <FileText />
                  <span>Draft LC Review</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "supplier-docs"}
                  onClick={() => onSectionChange("supplier-docs")}
                  tooltip="Supplier Doc Review"
                >
                  <ShieldCheck />
                  <span>Supplier Doc Review</span>
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
                  isActive={activeSection === "billing"}
                  onClick={() => onSectionChange("billing")}
                  tooltip="Billing"
                >
                  <CreditCard />
                  <span>Billing</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={activeSection === "settings"}
                  onClick={() => onSectionChange("settings")}
                  tooltip="Settings"
                >
                  <Settings />
                  <span>Settings</span>
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
                  {displayName?.charAt(0).toUpperCase() ||
                    user.email?.charAt(0).toUpperCase() ||
                    "U"}
                </div>
                <div className="flex flex-col gap-0.5 leading-none flex-1 min-w-0">
                  <span className="truncate font-medium text-sm">
                    {displayName || user.email}
                  </span>
                  <span className="text-xs text-muted-foreground capitalize">
                    {user.role === "admin" ? "Admin" : "Importer"}
                  </span>
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
