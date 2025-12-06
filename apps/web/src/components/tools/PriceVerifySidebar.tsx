/**
 * PriceVerifySidebar - Navigation component for Price Verify Dashboard
 * Follows the ExporterSidebar pattern for consistency
 */
import { 
  DollarSign,
  Home,
  Plus,
  ListChecks,
  Package,
  TrendingUp,
  History,
  BarChart3,
  FileText,
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
import { useUserRole } from "@/hooks/use-user-role";
import { Button } from "@/components/ui/button";

interface PriceVerifySidebarProps extends React.ComponentProps<typeof Sidebar> {}

export function PriceVerifySidebar({ ...props }: PriceVerifySidebarProps) {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { isAdmin, canAccessAdminPanels } = useUserRole();
  
  const isActive = (url: string) => {
    if (url === "/price-verify/dashboard") {
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

  const showAdmin = isAdmin || canAccessAdminPanels;

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
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500">
                  <DollarSign className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">Price Verify</span>
                  <span className="text-xs text-muted-foreground">TBML Detection</span>
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Verification</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/price-verify/dashboard") && location.pathname === "/price-verify/dashboard"}
                  asChild
                >
                  <Link to="/price-verify/dashboard">
                    <Home />
                    <span>Overview</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/price-verify/dashboard/verify")}
                  asChild
                >
                  <Link to="/price-verify/dashboard/verify">
                    <Plus />
                    <span>New Verification</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/price-verify/dashboard/batch")}
                  asChild
                >
                  <Link to="/price-verify/dashboard/batch">
                    <ListChecks />
                    <span>Batch Verify</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup>
          <SidebarGroupLabel>Data</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/price-verify/dashboard/commodities")}
                  asChild
                >
                  <Link to="/price-verify/dashboard/commodities">
                    <Package />
                    <span>Commodities</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/price-verify/dashboard/prices")}
                  asChild
                >
                  <Link to="/price-verify/dashboard/prices">
                    <TrendingUp />
                    <span>Market Prices</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/price-verify/dashboard/history")}
                  asChild
                >
                  <Link to="/price-verify/dashboard/history">
                    <History />
                    <span>History</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Insights</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/price-verify/dashboard/analytics")}
                  asChild
                >
                  <Link to="/price-verify/dashboard/analytics">
                    <BarChart3 />
                    <span>Analytics</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/price-verify/dashboard/reports")}
                  asChild
                >
                  <Link to="/price-verify/dashboard/reports">
                    <FileText />
                    <span>Reports</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {showAdmin && (
          <SidebarGroup>
            <SidebarGroupLabel>Admin</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={isActive("/price-verify/dashboard/admin")}
                    asChild
                  >
                    <Link to="/price-verify/dashboard/admin">
                      <Shield />
                      <span>Admin Panel</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
        
        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/price-verify/dashboard/settings")}
                  asChild
                >
                  <Link to="/price-verify/dashboard/settings">
                    <Settings />
                    <span>Settings</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/price-verify/dashboard/help")}
                  asChild
                >
                  <Link to="/price-verify/dashboard/help">
                    <HelpCircle />
                    <span>Help</span>
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

export default PriceVerifySidebar;

