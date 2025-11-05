import * as React from "react";
import { Link, useLocation } from "react-router-dom";
// Inline cn function to avoid import/bundling issues
function cn(...classes: (string | undefined | null | boolean | Record<string, boolean>)[]): string {
  return classes
    .filter(Boolean)
    .map((cls) => {
      if (typeof cls === 'string') return cls;
      if (typeof cls === 'object' && cls !== null) {
        return Object.entries(cls)
          .filter(([_, val]) => val)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join(' ');
}
;
import { Button } from "@/components/ui/button";
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuIndicator,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
  NavigationMenuViewport,
} from "@/components/ui/navigation-menu";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/use-auth";
import { BarChart3, TrendingUp, Users, Shield, ChevronDown } from "lucide-react";
import type { Role } from "@/types/analytics";

interface AnalyticsNavProps {
  className?: string;
}

const getAnalyticsRoutes = (role: Role) => {
  const baseRoutes = [
    {
      href: "/lcopilot/analytics",
      label: "Overview",
      icon: BarChart3,
      description: "Complete analytics dashboard"
    }
  ];

  switch (role) {
    case "exporter":
      return [
        ...baseRoutes,
        {
          href: "/lcopilot/analytics/exporter",
          label: "My Performance",
          icon: TrendingUp,
          description: "Personal export analytics"
        }
      ];

    case "importer":
      return [
        ...baseRoutes,
        {
          href: "/lcopilot/analytics/importer",
          label: "My Performance",
          icon: TrendingUp,
          description: "Personal import analytics"
        }
      ];

    case "bank":
      return [
        ...baseRoutes,
        {
          href: "/lcopilot/analytics/bank",
          label: "Bank Dashboard",
          icon: Shield,
          description: "System-wide bank analytics"
        }
      ];

    case "admin":
      return [
        ...baseRoutes,
        {
          href: "/lcopilot/analytics/bank",
          label: "System Analytics",
          icon: Users,
          description: "Complete system overview"
        }
      ];

    default:
      return baseRoutes;
  }
};

export function AnalyticsNav({ className }: AnalyticsNavProps) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) return null;

  const routes = getAnalyticsRoutes(user.role as Role);
  const currentRoute = routes.find(route => route.href === location.pathname);

  return (
    <div className={cn("flex items-center", className)}>
      {/* Desktop Navigation */}
      <NavigationMenu className="hidden md:flex">
        <NavigationMenuList>
          <NavigationMenuItem>
            <NavigationMenuTrigger>
              <BarChart3 className="mr-2 h-4 w-4" />
              Analytics
            </NavigationMenuTrigger>
            <NavigationMenuContent>
              <ul className="grid w-[400px] gap-3 p-4 md:w-[500px] md:grid-cols-2 lg:w-[600px]">
                {routes.map((route) => {
                  const IconComponent = route.icon;
                  return (
                    <li key={route.href}>
                      <NavigationMenuLink asChild>
                        <Link
                          className={cn(
                            "block select-none space-y-1 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground",
                            location.pathname === route.href && "bg-accent"
                          )}
                          to={route.href}
                        >
                          <div className="flex items-center gap-2">
                            <IconComponent className="h-4 w-4" />
                            <div className="text-sm font-medium leading-none">
                              {route.label}
                            </div>
                          </div>
                          <p className="line-clamp-2 text-sm leading-snug text-muted-foreground">
                            {route.description}
                          </p>
                        </Link>
                      </NavigationMenuLink>
                    </li>
                  );
                })}
              </ul>
            </NavigationMenuContent>
          </NavigationMenuItem>
        </NavigationMenuList>
      </NavigationMenu>

      {/* Mobile Navigation */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild className="md:hidden">
          <Button variant="outline" size="sm">
            <BarChart3 className="mr-2 h-4 w-4" />
            {currentRoute?.label || "Analytics"}
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-[200px]">
          <DropdownMenuLabel>Analytics</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {routes.map((route) => {
            const IconComponent = route.icon;
            return (
              <DropdownMenuItem key={route.href} asChild>
                <Link
                  to={route.href}
                  className={cn(
                    "flex items-center gap-2 w-full",
                    location.pathname === route.href && "bg-accent"
                  )}
                >
                  <IconComponent className="h-4 w-4" />
                  {route.label}
                </Link>
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

// Breadcrumb component for analytics pages
export function AnalyticsBreadcrumb() {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) return null;

  const routes = getAnalyticsRoutes(user.role as Role);
  const currentRoute = routes.find(route => route.href === location.pathname);

  if (!currentRoute) return null;

  return (
    <div className="flex items-center space-x-1 text-sm text-muted-foreground">
      <Link to="/lcopilot/dashboard" className="hover:text-foreground">
        Dashboard
      </Link>
      <span>/</span>
      <span className="text-foreground font-medium">{currentRoute.label}</span>
    </div>
  );
}