/**
 * SanctionsSidebar - Navigation component for Sanctions Screener Dashboard
 * Follows the ExporterSidebar pattern for consistency
 */
import { 
  LayoutDashboard,
  Users,
  Ship,
  Package,
  Upload,
  History,
  FileCheck,
  Bell,
  Key,
  Settings,
  HelpCircle,
  Shield,
  LogOut,
  ArrowLeft,
} from "lucide-react";
import { useLocation, Link } from "react-router-dom";
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
import { Button } from "@/components/ui/button";

interface SanctionsSidebarProps extends React.ComponentProps<typeof Sidebar> {}

export function SanctionsSidebar({ ...props }: SanctionsSidebarProps) {
  const location = useLocation();
  const { user, logout } = useAuth();
  
  const isActive = (url: string) => {
    if (url === "/sanctions/dashboard") {
      return location.pathname === url;
    }
    return location.pathname.startsWith(url);
  };

  const handleLogout = async (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    try {
      await logout();
    } catch (error) {
      console.warn('Logout failed:', error);
      window.location.href = '/login';
    }
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
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-red-500/10 text-red-500">
                  <Shield className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">Sanctions Screener</span>
                  <span className="text-xs text-muted-foreground">Compliance Tool</span>
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Screening</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/sanctions/dashboard") && location.pathname === "/sanctions/dashboard"}
                  asChild
                >
                  <Link to="/sanctions/dashboard">
                    <LayoutDashboard />
                    <span>Overview</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/sanctions/dashboard/screen/party")}
                  asChild
                >
                  <Link to="/sanctions/dashboard/screen/party">
                    <Users />
                    <span>Screen Party</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/sanctions/dashboard/screen/vessel")}
                  asChild
                >
                  <Link to="/sanctions/dashboard/screen/vessel">
                    <Ship />
                    <span>Screen Vessel</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/sanctions/dashboard/screen/goods")}
                  asChild
                >
                  <Link to="/sanctions/dashboard/screen/goods">
                    <Package />
                    <span>Screen Goods</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup>
          <SidebarGroupLabel>Management</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/sanctions/dashboard/batch")}
                  asChild
                >
                  <Link to="/sanctions/dashboard/batch">
                    <Upload />
                    <span>Batch Upload</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/sanctions/dashboard/history")}
                  asChild
                >
                  <Link to="/sanctions/dashboard/history">
                    <History />
                    <span>History</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/sanctions/dashboard/certificates")}
                  asChild
                >
                  <Link to="/sanctions/dashboard/certificates">
                    <FileCheck />
                    <span>Certificates</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/sanctions/dashboard/watchlist")}
                  asChild
                >
                  <Link to="/sanctions/dashboard/watchlist">
                    <Bell />
                    <span>Watchlist</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Integration</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/sanctions/dashboard/api")}
                  asChild
                >
                  <Link to="/sanctions/dashboard/api">
                    <Key />
                    <span>API Access</span>
                  </Link>
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
                  isActive={isActive("/sanctions/dashboard/settings")}
                  asChild
                >
                  <Link to="/sanctions/dashboard/settings">
                    <Settings />
                    <span>Settings</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/sanctions/dashboard/help")}
                  asChild
                >
                  <Link to="/sanctions/dashboard/help">
                    <HelpCircle />
                    <span>Help & FAQ</span>
                  </Link>
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
                  <span className="text-xs text-muted-foreground capitalize">{user.role || 'User'}</span>
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

export default SanctionsSidebar;

