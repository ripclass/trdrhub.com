/**
 * DocGeneratorSidebar - Navigation component for Doc Generator Dashboard
 * Follows the ExporterSidebar pattern for consistency
 */
import { 
  FileText,
  Plus,
  FolderOpen,
  LayoutTemplate,
  Package,
  Users,
  PenTool,
  Building2,
  Award,
  Palette,
  Settings,
  HelpCircle,
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

interface DocGeneratorSidebarProps extends React.ComponentProps<typeof Sidebar> {}

export function DocGeneratorSidebar({ ...props }: DocGeneratorSidebarProps) {
  const location = useLocation();
  const { user, logout } = useAuth();
  
  const isActive = (url: string) => {
    if (url === "/doc-generator/dashboard") {
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
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-500">
                  <FileText className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">Doc Generator</span>
                  <span className="text-xs text-muted-foreground">Shipping Documents</span>
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Documents</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/doc-generator/dashboard") && location.pathname === "/doc-generator/dashboard"}
                  asChild
                >
                  <Link to="/doc-generator/dashboard">
                    <FolderOpen />
                    <span>All Documents</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/doc-generator/dashboard/new")}
                  asChild
                >
                  <Link to="/doc-generator/dashboard/new">
                    <Plus />
                    <span>Create New</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        <SidebarGroup>
          <SidebarGroupLabel>Quick Entry</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/doc-generator/dashboard/templates")}
                  asChild
                >
                  <Link to="/doc-generator/dashboard/templates">
                    <LayoutTemplate />
                    <span>Templates</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/doc-generator/dashboard/products")}
                  asChild
                >
                  <Link to="/doc-generator/dashboard/products">
                    <Package />
                    <span>Product Catalog</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/doc-generator/dashboard/buyers")}
                  asChild
                >
                  <Link to="/doc-generator/dashboard/buyers">
                    <Users />
                    <span>Buyer Directory</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Advanced</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/doc-generator/dashboard/signatures")}
                  asChild
                >
                  <Link to="/doc-generator/dashboard/signatures">
                    <PenTool />
                    <span>Digital Signatures</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/doc-generator/dashboard/bank-formats")}
                  asChild
                >
                  <Link to="/doc-generator/dashboard/bank-formats">
                    <Building2 />
                    <span>Bank Formats</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/doc-generator/dashboard/certificates")}
                  asChild
                >
                  <Link to="/doc-generator/dashboard/certificates">
                    <Award />
                    <span>GSP / EUR.1 Certs</span>
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
                  isActive={isActive("/doc-generator/dashboard/branding")}
                  asChild
                >
                  <Link to="/doc-generator/dashboard/branding">
                    <Palette />
                    <span>Company Branding</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={isActive("/doc-generator/dashboard/help")}
                  asChild
                >
                  <Link to="/doc-generator/dashboard/help">
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

export default DocGeneratorSidebar;

