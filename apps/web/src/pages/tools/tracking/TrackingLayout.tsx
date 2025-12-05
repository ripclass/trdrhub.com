/**
 * Tracking Dashboard Layout
 * 
 * A professional dashboard with sidebar navigation for the Container & Vessel Tracking tool.
 * Built with shadcn/ui sidebar components - mirrors Price Verify Dashboard pattern.
 */

import { useState, useEffect, useCallback } from "react";
import { Link, useLocation, Outlet, useNavigate } from "react-router-dom";
import {
  Ship,
  Search,
  BarChart3,
  History,
  Settings,
  HelpCircle,
  Package,
  Bell,
  Home,
  Plus,
  MapPin,
  Anchor,
  Clock,
  AlertTriangle,
  ArrowLeft,
  Command,
  Keyboard,
  Shield,
  Container,
  Route,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useUserRole } from "@/hooks/use-user-role";
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
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
  SidebarRail,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// Navigation items
const navItems = {
  main: [
    {
      title: "Overview",
      url: "/tracking/dashboard",
      icon: Home,
    },
    {
      title: "Track Container",
      url: "/tracking/dashboard/search",
      icon: Container,
    },
    {
      title: "Track Vessel",
      url: "/tracking/dashboard/vessel-search",
      icon: Ship,
    },
  ],
  monitoring: [
    {
      title: "Active Shipments",
      url: "/tracking/dashboard/active",
      icon: Package,
    },
    {
      title: "Route Map",
      url: "/tracking/dashboard/map",
      icon: MapPin,
    },
    {
      title: "Port Schedule",
      url: "/tracking/dashboard/ports",
      icon: Anchor,
    },
  ],
  alerts: [
    {
      title: "Alerts",
      url: "/tracking/dashboard/alerts",
      icon: Bell,
    },
    {
      title: "Exceptions",
      url: "/tracking/dashboard/exceptions",
      icon: AlertTriangle,
    },
    {
      title: "History",
      url: "/tracking/dashboard/history",
      icon: History,
    },
  ],
  insights: [
    {
      title: "Analytics",
      url: "/tracking/dashboard/analytics",
      icon: BarChart3,
    },
    {
      title: "Performance",
      url: "/tracking/dashboard/performance",
      icon: Clock,
    },
  ],
  support: [
    {
      title: "Settings",
      url: "/tracking/dashboard/settings",
      icon: Settings,
    },
    {
      title: "Help",
      url: "/tracking/dashboard/help",
      icon: HelpCircle,
    },
  ],
};

export default function TrackingLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { isAdmin, canAccessAdminPanels } = useUserRole();
  const [notifications] = useState(2);
  const [commandOpen, setCommandOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  // Get user display info
  const userName = user?.full_name || user?.email?.split("@")[0] || "Guest User";
  const userInitials = userName.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2) || "GU";

  // Get current page title for breadcrumb
  const getCurrentPageTitle = () => {
    const allItems = [...navItems.main, ...navItems.monitoring, ...navItems.alerts, ...navItems.insights, ...navItems.support];
    const currentItem = allItems.find(item => item.url === location.pathname);
    return currentItem?.title || "Dashboard";
  };

  // Keyboard shortcuts
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K - Open command palette
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandOpen(open => !open);
      }
      // Ctrl+Enter or Cmd+Enter - Go to Track Container
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        navigate("/tracking/dashboard/search");
      }
      // ? key - Show keyboard shortcuts
      if (e.key === "?" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const target = e.target as HTMLElement;
        if (target.tagName !== "INPUT" && target.tagName !== "TEXTAREA") {
          e.preventDefault();
          setShortcutsOpen(true);
        }
      }
      // Escape - Close dialogs
      if (e.key === "Escape") {
        setCommandOpen(false);
        setShortcutsOpen(false);
      }
    };
    
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [navigate]);

  // Command palette navigation
  const runCommand = useCallback((command: () => void) => {
    setCommandOpen(false);
    command();
  }, []);

  return (
    <SidebarProvider>
      <Sidebar className="border-r border-sidebar-border">
        <SidebarHeader className="border-b border-sidebar-border">
          <div className="flex flex-col gap-2 px-2 py-2">
            <Link 
              to="/hub" 
              className="flex items-center gap-2 text-xs text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors"
            >
              <ArrowLeft className="h-3 w-3" />
              Back to Hub
            </Link>
            <Link to="/tracking" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500">
                <Ship className="h-6 w-6 text-white" />
              </div>
              <div className="flex flex-col">
                <span className="font-semibold text-sidebar-foreground">Container Tracker</span>
                <span className="text-xs text-sidebar-foreground/60">by TRDR Hub</span>
              </div>
            </Link>
          </div>
        </SidebarHeader>

        <SidebarContent>
          {/* Main Navigation */}
          <SidebarGroup>
            <SidebarGroupLabel>Tracking</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {navItems.main.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild 
                      isActive={location.pathname === item.url}
                      tooltip={item.title}
                    >
                      <Link to={item.url}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          {/* Monitoring Navigation */}
          <SidebarGroup>
            <SidebarGroupLabel>Monitoring</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {navItems.monitoring.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild 
                      isActive={location.pathname === item.url}
                      tooltip={item.title}
                    >
                      <Link to={item.url}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          {/* Alerts Navigation */}
          <SidebarGroup>
            <SidebarGroupLabel>Notifications</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {navItems.alerts.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild 
                      isActive={location.pathname === item.url}
                      tooltip={item.title}
                    >
                      <Link to={item.url}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                        {item.title === "Alerts" && notifications > 0 && (
                          <Badge variant="destructive" className="ml-auto h-5 px-1.5 text-xs">
                            {notifications}
                          </Badge>
                        )}
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          {/* Insights Navigation */}
          <SidebarGroup>
            <SidebarGroupLabel>Insights</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {navItems.insights.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild 
                      isActive={location.pathname === item.url}
                      tooltip={item.title}
                    >
                      <Link to={item.url}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          {/* Support Navigation */}
          <SidebarGroup className="mt-auto">
            <SidebarGroupContent>
              <SidebarMenu>
                {navItems.support.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild 
                      isActive={location.pathname === item.url}
                      tooltip={item.title}
                    >
                      <Link to={item.url}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter className="border-t border-sidebar-border">
          <SidebarMenu>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <SidebarMenuButton className="w-full">
                    <Avatar className="h-6 w-6">
                      <AvatarFallback className="text-xs bg-blue-500 text-white">
                        {userInitials}
                      </AvatarFallback>
                    </Avatar>
                    <span className="truncate">{userName}</span>
                  </SidebarMenuButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56">
                  <DropdownMenuLabel>My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to="/hub/settings">Settings</Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/hub/billing">Billing</Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to="/hub">Back to Hub</Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    className="text-red-500 focus:text-red-500"
                    onClick={() => {
                      logout().then(() => {
                        window.location.href = "/login";
                      });
                    }}
                  >
                    Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>

      <SidebarInset>
        {/* Header */}
        <header className="flex h-14 items-center gap-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-6">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-6" />
          
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link to="/tracking/dashboard">Container Tracker</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{getCurrentPageTitle()}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="hidden md:flex items-center gap-2 text-muted-foreground"
              onClick={() => setCommandOpen(true)}
            >
              <Search className="h-4 w-4" />
              <span>Search...</span>
              <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground sm:flex">
                <span className="text-xs">⌘</span>K
              </kbd>
            </Button>
            
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-4 w-4" />
              {notifications > 0 && (
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground flex items-center justify-center">
                  {notifications}
                </span>
              )}
            </Button>

            <ThemeToggle />
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </SidebarInset>

      {/* Command Palette */}
      <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
        <CommandInput placeholder="Type a command or search..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Actions">
            <CommandItem onSelect={() => runCommand(() => navigate("/tracking/dashboard/search"))}>
              <Container className="mr-2 h-4 w-4" />
              Track Container
            </CommandItem>
            <CommandItem onSelect={() => runCommand(() => navigate("/tracking/dashboard/vessel-search"))}>
              <Ship className="mr-2 h-4 w-4" />
              Track Vessel
            </CommandItem>
            <CommandItem onSelect={() => runCommand(() => navigate("/tracking/dashboard/alerts"))}>
              <Bell className="mr-2 h-4 w-4" />
              View Alerts
            </CommandItem>
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Navigation">
            <CommandItem onSelect={() => runCommand(() => navigate("/tracking/dashboard"))}>
              <Home className="mr-2 h-4 w-4" />
              Overview
            </CommandItem>
            <CommandItem onSelect={() => runCommand(() => navigate("/tracking/dashboard/active"))}>
              <Package className="mr-2 h-4 w-4" />
              Active Shipments
            </CommandItem>
            <CommandItem onSelect={() => runCommand(() => navigate("/tracking/dashboard/analytics"))}>
              <BarChart3 className="mr-2 h-4 w-4" />
              Analytics
            </CommandItem>
            <CommandItem onSelect={() => runCommand(() => navigate("/hub"))}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Hub
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>

      {/* Keyboard Shortcuts Dialog */}
      <Dialog open={shortcutsOpen} onOpenChange={setShortcutsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Keyboard className="h-5 w-5" />
              Keyboard Shortcuts
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="flex items-center justify-between">
              <span>Open command palette</span>
              <kbd className="px-2 py-1 bg-muted rounded text-sm">⌘K</kbd>
            </div>
            <div className="flex items-center justify-between">
              <span>Track new container</span>
              <kbd className="px-2 py-1 bg-muted rounded text-sm">⌘↵</kbd>
            </div>
            <div className="flex items-center justify-between">
              <span>Show shortcuts</span>
              <kbd className="px-2 py-1 bg-muted rounded text-sm">?</kbd>
            </div>
            <div className="flex items-center justify-between">
              <span>Close dialogs</span>
              <kbd className="px-2 py-1 bg-muted rounded text-sm">Esc</kbd>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </SidebarProvider>
  );
}

