/**
 * Hub Layout - Unified layout with sidebar for all Hub pages
 */

import { useState, useEffect } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Home,
  CreditCard,
  Users,
  Settings,
  BarChart3,
  FileCheck,
  DollarSign,
  Package,
  Shield,
  Ship,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  LogOut,
  HelpCircle,
  Menu,
  X,
  Zap,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";

interface NavItem {
  id: string;
  label: string;
  icon: React.ElementType;
  href: string;
  badge?: string;
  badgeVariant?: "default" | "success" | "warning" | "destructive";
  external?: boolean;
  disabled?: boolean;
}

interface NavSection {
  title?: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    items: [
      { id: "home", label: "Home", icon: Home, href: "/hub" },
      { id: "usage", label: "Usage", icon: BarChart3, href: "/hub/usage" },
    ],
  },
  {
    title: "Tools",
    items: [
      { 
        id: "lcopilot", 
        label: "LCopilot", 
        icon: FileCheck, 
        href: "/lcopilot/dashboard",
        badge: "Active",
        badgeVariant: "success",
      },
      { 
        id: "price-verify", 
        label: "Price Verify", 
        icon: DollarSign, 
        href: "/price-verify/dashboard",
        badge: "Active",
        badgeVariant: "success",
      },
      { 
        id: "hs-code", 
        label: "HS Code Finder", 
        icon: Package, 
        href: "/tools/hs-code",
        badge: "Soon",
        badgeVariant: "default",
        disabled: true,
      },
      { 
        id: "sanctions", 
        label: "Sanctions", 
        icon: Shield, 
        href: "/tools/sanctions",
        badge: "Soon",
        badgeVariant: "default",
        disabled: true,
      },
      { 
        id: "tracking", 
        label: "Container Track", 
        icon: Ship, 
        href: "/tools/container-tracker",
        badge: "Soon",
        badgeVariant: "default",
        disabled: true,
      },
    ],
  },
  {
    title: "Account",
    items: [
      { id: "billing", label: "Billing", icon: CreditCard, href: "/hub/billing" },
      { id: "team", label: "Team", icon: Users, href: "/hub/team" },
      { id: "settings", label: "Settings", icon: Settings, href: "/hub/settings" },
    ],
  },
];

export default function HubLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, isLoading } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [planName, setPlanName] = useState("Pay-as-you-go");

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !user) {
      navigate("/login?returnUrl=" + encodeURIComponent(location.pathname));
    }
  }, [user, isLoading, navigate, location.pathname]);

  const isActive = (href: string) => {
    if (href === "/hub") {
      return location.pathname === "/hub" || location.pathname === "/hub/home";
    }
    return location.pathname.startsWith(href);
  };

  // Get user name from auth
  const userName = user?.full_name || user?.email?.split("@")[0] || "User";

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  // Show nothing while loading auth
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        {/* Mobile Header */}
        <header className="lg:hidden border-b border-white/5 bg-slate-900/80 backdrop-blur-xl sticky top-0 z-50">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setMobileOpen(!mobileOpen)}
                className="text-slate-400"
              >
                {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </Button>
              <Link to="/hub" className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <span className="text-lg font-bold text-white">TRDR Hub</span>
              </Link>
            </div>
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-gradient-to-br from-blue-500 to-emerald-500 text-white text-sm">
                {userName.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
          </div>
        </header>

        <div className="flex">
          {/* Sidebar */}
          <aside
            className={cn(
              "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-white/5 bg-slate-900/95 backdrop-blur-xl transition-all duration-300",
              collapsed ? "w-[70px]" : "w-[260px]",
              "hidden lg:flex",
              mobileOpen && "flex lg:hidden w-[280px]"
            )}
          >
            {/* Logo */}
            <div className={cn(
              "flex items-center gap-3 px-4 py-5 border-b border-white/5",
              collapsed && "justify-center px-2"
            )}>
              <Link to="/hub" className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                {!collapsed && (
                  <div>
                    <span className="text-lg font-bold text-white">TRDR Hub</span>
                    <Badge 
                      variant="outline" 
                      className="ml-2 text-[10px] border-emerald-500/30 text-emerald-400"
                    >
                      {planName}
                    </Badge>
                  </div>
                )}
              </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto py-4 px-3">
              {NAV_SECTIONS.map((section, sectionIdx) => (
                <div key={sectionIdx} className={cn(sectionIdx > 0 && "mt-6")}>
                  {section.title && !collapsed && (
                    <h3 className="px-3 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      {section.title}
                    </h3>
                  )}
                  {section.title && collapsed && (
                    <Separator className="mb-2 bg-white/5" />
                  )}
                  <div className="space-y-1">
                    {section.items.map((item) => {
                      const Icon = item.icon;
                      const active = isActive(item.href);
                      const NavLink = item.disabled ? 'div' : Link;

                      const linkContent = (
                        <div
                          className={cn(
                            "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all",
                            active
                              ? "bg-gradient-to-r from-blue-500/20 to-emerald-500/20 text-white"
                              : item.disabled
                              ? "text-slate-600 cursor-not-allowed"
                              : "text-slate-400 hover:text-white hover:bg-white/5",
                            collapsed && "justify-center px-2"
                          )}
                        >
                          <Icon className={cn(
                            "w-5 h-5 flex-shrink-0",
                            active && "text-emerald-400"
                          )} />
                          {!collapsed && (
                            <>
                              <span className="flex-1 text-sm font-medium">{item.label}</span>
                              {item.badge && (
                                <Badge
                                  variant="outline"
                                  className={cn(
                                    "text-[10px] px-1.5",
                                    item.badgeVariant === "success" && "border-emerald-500/30 text-emerald-400",
                                    item.badgeVariant === "warning" && "border-amber-500/30 text-amber-400",
                                    item.badgeVariant === "default" && "border-slate-500/30 text-slate-500"
                                  )}
                                >
                                  {item.disabled && <Lock className="w-2.5 h-2.5 mr-0.5" />}
                                  {item.badge}
                                </Badge>
                              )}
                            </>
                          )}
                        </div>
                      );

                      if (collapsed) {
                        return (
                          <Tooltip key={item.id} delayDuration={0}>
                            <TooltipTrigger asChild>
                              {item.disabled ? (
                                <div>{linkContent}</div>
                              ) : (
                                <Link to={item.href}>{linkContent}</Link>
                              )}
                            </TooltipTrigger>
                            <TooltipContent side="right" className="bg-slate-800 border-white/10">
                              <p>{item.label}</p>
                              {item.badge && (
                                <span className="text-xs text-slate-400 ml-1">({item.badge})</span>
                              )}
                            </TooltipContent>
                          </Tooltip>
                        );
                      }

                      return item.disabled ? (
                        <div key={item.id}>{linkContent}</div>
                      ) : (
                        <Link key={item.id} to={item.href} onClick={() => setMobileOpen(false)}>
                          {linkContent}
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}
            </nav>

            {/* Bottom Section */}
            <div className="border-t border-white/5 p-3 space-y-2">
              {!collapsed && (
                <>
                  <Link
                    to="/support"
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                  >
                    <HelpCircle className="w-5 h-5" />
                    <span className="text-sm">Help & Support</span>
                  </Link>
                </>
              )}
              
              {/* User Profile */}
              <div className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg bg-slate-800/50",
                collapsed && "justify-center px-2"
              )}>
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-gradient-to-br from-blue-500 to-emerald-500 text-white text-sm">
                    {userName.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                {!collapsed && (
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{userName}</p>
                    <p className="text-xs text-slate-400 truncate">{planName}</p>
                  </div>
                )}
                {!collapsed && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-slate-400 hover:text-white h-8 w-8"
                    onClick={handleLogout}
                  >
                    <LogOut className="w-4 h-4" />
                  </Button>
                )}
              </div>

              {/* Collapse Toggle */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCollapsed(!collapsed)}
                className={cn(
                  "w-full text-slate-400 hover:text-white hover:bg-white/5",
                  collapsed && "px-2"
                )}
              >
                {collapsed ? (
                  <ChevronRight className="w-4 h-4" />
                ) : (
                  <>
                    <ChevronLeft className="w-4 h-4 mr-2" />
                    Collapse
                  </>
                )}
              </Button>
            </div>
          </aside>

          {/* Mobile Overlay */}
          {mobileOpen && (
            <div
              className="fixed inset-0 bg-black/50 z-30 lg:hidden"
              onClick={() => setMobileOpen(false)}
            />
          )}

          {/* Main Content */}
          <main
            className={cn(
              "flex-1 min-h-screen transition-all duration-300",
              collapsed ? "lg:ml-[70px]" : "lg:ml-[260px]"
            )}
          >
            <Outlet />
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}

