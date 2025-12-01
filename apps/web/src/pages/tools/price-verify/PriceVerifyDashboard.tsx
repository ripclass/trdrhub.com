/**
 * Price Verify Dashboard
 * 
 * A professional dashboard with sidebar navigation for the Price Verification tool.
 * Built with shadcn/ui sidebar components.
 */

import { useState } from "react";
import { Link, useLocation, Outlet } from "react-router-dom";
import {
  DollarSign,
  Search,
  BarChart3,
  History,
  Settings,
  HelpCircle,
  Package,
  TrendingUp,
  FileText,
  ChevronRight,
  Home,
  Plus,
  ListChecks,
  Bell,
} from "lucide-react";
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

// Navigation items
const navItems = {
  main: [
    {
      title: "Overview",
      url: "/price-verify/dashboard",
      icon: Home,
    },
    {
      title: "New Verification",
      url: "/price-verify/dashboard/verify",
      icon: Plus,
    },
    {
      title: "Batch Verify",
      url: "/price-verify/dashboard/batch",
      icon: ListChecks,
    },
  ],
  data: [
    {
      title: "Commodities",
      url: "/price-verify/dashboard/commodities",
      icon: Package,
    },
    {
      title: "Market Prices",
      url: "/price-verify/dashboard/prices",
      icon: TrendingUp,
    },
    {
      title: "History",
      url: "/price-verify/dashboard/history",
      icon: History,
    },
  ],
  reports: [
    {
      title: "Analytics",
      url: "/price-verify/dashboard/analytics",
      icon: BarChart3,
    },
    {
      title: "Reports",
      url: "/price-verify/dashboard/reports",
      icon: FileText,
    },
  ],
  support: [
    {
      title: "Settings",
      url: "/price-verify/dashboard/settings",
      icon: Settings,
    },
    {
      title: "Help",
      url: "/price-verify/dashboard/help",
      icon: HelpCircle,
    },
  ],
};

export default function PriceVerifyDashboard() {
  const location = useLocation();
  const [notifications] = useState(3);

  // Get current page title for breadcrumb
  const getCurrentPageTitle = () => {
    const allItems = [...navItems.main, ...navItems.data, ...navItems.reports, ...navItems.support];
    const currentItem = allItems.find(item => item.url === location.pathname);
    return currentItem?.title || "Dashboard";
  };

  return (
    <SidebarProvider>
      <Sidebar className="border-r border-sidebar-border">
        <SidebarHeader className="border-b border-sidebar-border">
          <Link to="/price-verify" className="flex items-center gap-3 px-2 py-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500">
              <DollarSign className="h-6 w-6 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-sidebar-foreground">Price Verify</span>
              <span className="text-xs text-sidebar-foreground/60">by TRDR Hub</span>
            </div>
          </Link>
        </SidebarHeader>

        <SidebarContent>
          {/* Main Navigation */}
          <SidebarGroup>
            <SidebarGroupLabel>Verification</SidebarGroupLabel>
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

          {/* Data Navigation */}
          <SidebarGroup>
            <SidebarGroupLabel>Data</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {navItems.data.map((item) => (
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

          {/* Reports Navigation */}
          <SidebarGroup>
            <SidebarGroupLabel>Insights</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {navItems.reports.map((item) => (
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
                  <SidebarMenuButton size="lg">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="bg-green-500 text-white">
                        PV
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-1 flex-col text-left text-sm leading-tight">
                      <span className="truncate font-medium">Guest User</span>
                      <span className="truncate text-xs text-muted-foreground">Free Plan</span>
                    </div>
                    <ChevronRight className="ml-auto h-4 w-4" />
                  </SidebarMenuButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent side="right" align="end" className="w-56">
                  <DropdownMenuLabel>My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <TrendingUp className="mr-2 h-4 w-4" />
                    Upgrade to Pro
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to="/">Back to TRDR Hub</Link>
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
        <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 transition-[width,height] ease-linear group-has-[[data-collapsible=icon]]/sidebar-wrapper:h-12">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem className="hidden md:block">
                <BreadcrumbLink asChild>
                  <Link to="/price-verify">Price Verify</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator className="hidden md:block" />
              <BreadcrumbItem>
                <BreadcrumbPage>{getCurrentPageTitle()}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="ml-auto flex items-center gap-2">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-4 w-4" />
              {notifications > 0 && (
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-red-500 text-[10px] font-medium text-white flex items-center justify-center">
                  {notifications}
                </span>
              )}
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/price-verify/dashboard/verify">
                <Plus className="h-4 w-4 mr-2" />
                New Verification
              </Link>
            </Button>
          </div>
        </header>

        {/* Main Content - Renders child routes */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

