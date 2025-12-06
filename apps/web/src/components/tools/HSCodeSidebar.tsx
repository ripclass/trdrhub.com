/**
 * HSCodeSidebar - Navigation component for HS Code Finder Dashboard
 * Follows the ExporterSidebar pattern for consistency
 */
import { 
  TrendingUp,
  Search,
  BookOpen,
  Calculator,
  GitCompare,
  Globe,
  Globe2,
  FileCheck,
  ShieldCheck,
  Shield,
  FileText,
  Scale,
  PieChart,
  Gavel,
  Bell,
  History,
  Star,
  Users,
  Settings,
  HelpCircle,
  Package,
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
import { Badge } from "@/components/ui/badge";

interface HSCodeSidebarProps extends React.ComponentProps<typeof Sidebar> {}

export function HSCodeSidebar({ ...props }: HSCodeSidebarProps) {
  const location = useLocation();
  const { user, logout } = useAuth();
  
  const isActive = (url: string) => {
    if (url === "/hs-code/dashboard") {
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
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-purple-500/10 text-purple-500">
                  <Package className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">HS Code Finder</span>
                  <span className="text-xs text-muted-foreground">Classification Tool</span>
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Classification</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard") && location.pathname === "/hs-code/dashboard"}
                  asChild
                >
                  <Link to="/hs-code/dashboard">
                    <TrendingUp />
                    <span>Overview</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/classify")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/classify">
                    <Search />
                    <span>Classify Product</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/search")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/search">
                    <BookOpen />
                    <span>Search HS Codes</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/duty")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/duty">
                    <Calculator />
                    <span>Duty Calculator</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/compare")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/compare">
                    <GitCompare />
                    <span>Compare Products</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup>
          <SidebarGroupLabel>Trade Agreements</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/fta")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/fta">
                    <Globe />
                    <span>FTA Eligibility</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/usmca")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/usmca">
                    <Globe2 />
                    <span>USMCA Calculator</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/roo")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/roo">
                    <FileCheck />
                    <span>Rules of Origin</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Compliance Suite</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/compliance-suite")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/compliance-suite">
                    <ShieldCheck />
                    <span>Compliance Dashboard</span>
                    <Badge variant="secondary" className="ml-auto text-[10px] px-1.5">New</Badge>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/export-controls")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/export-controls">
                    <Shield />
                    <span>Export Controls</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/section-301")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/section-301">
                    <FileText />
                    <span>Section 301</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/ad-cvd")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/ad-cvd">
                    <Scale />
                    <span>AD/CVD Orders</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/quotas")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/quotas">
                    <PieChart />
                    <span>Quota Status</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Research & Alerts</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/rulings")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/rulings">
                    <Gavel />
                    <span>Binding Rulings</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/alerts")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/alerts">
                    <Bell />
                    <span>Rate Alerts</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>My Data</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/history")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/history">
                    <History />
                    <span>History</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/favorites")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/favorites">
                    <Star />
                    <span>Favorites</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/bulk")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/bulk">
                    <FileText />
                    <span>Bulk Upload</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/teams")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/teams">
                    <Users />
                    <span>Team Management</span>
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
                  isActive={isActive("/hs-code/dashboard/settings")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/settings">
                    <Settings />
                    <span>Settings</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/hs-code/dashboard/help")}
                  asChild
                >
                  <Link to="/hs-code/dashboard/help">
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

export default HSCodeSidebar;

