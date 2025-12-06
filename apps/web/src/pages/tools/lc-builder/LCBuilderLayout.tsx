/**
 * LC Builder Dashboard Layout
 * 
 * Sidebar layout for the LC application builder tool.
 */

import { useState, useCallback, useEffect } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import {
  FileText,
  Plus,
  FolderOpen,
  Settings,
  HelpCircle,
  ArrowLeft,
  Search,
  ChevronDown,
  LogOut,
  BookOpen,
  FileCheck,
  Eye,
  Download,
  AlertTriangle,
  History,
  Users,
  Building2,
  Zap,
  ClipboardCheck,
  Send,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useAuth } from "@/hooks/use-auth";

// Navigation items
const navItems = [
  {
    title: "Applications",
    items: [
      {
        title: "All Applications",
        href: "/lc-builder/dashboard",
        icon: FolderOpen,
      },
      {
        title: "Create New",
        href: "/lc-builder/dashboard/new",
        icon: Plus,
      },
    ],
  },
  {
    title: "Workflow",
    items: [
      {
        title: "Approval Queue",
        href: "/lc-builder/dashboard/approvals",
        icon: ClipboardCheck,
        badge: "New",
      },
    ],
  },
  {
    title: "Library",
    items: [
      {
        title: "Clause Library",
        href: "/lc-builder/dashboard/clauses",
        icon: BookOpen,
      },
      {
        title: "Templates",
        href: "/lc-builder/dashboard/templates",
        icon: FileText,
      },
    ],
  },
  {
    title: "Quick Entry",
    items: [
      {
        title: "Applicant Profiles",
        href: "/lc-builder/dashboard/applicants",
        icon: Building2,
      },
      {
        title: "Beneficiary Directory",
        href: "/lc-builder/dashboard/beneficiaries",
        icon: Users,
      },
    ],
  },
  {
    title: "Tools",
    items: [
      {
        title: "MT700 Reference",
        href: "/lc-builder/dashboard/mt700-reference",
        icon: FileCheck,
      },
      {
        title: "Risk Calculator",
        href: "/lc-builder/dashboard/risk",
        icon: AlertTriangle,
      },
      {
        title: "Version History",
        href: "/lc-builder/dashboard/history",
        icon: History,
        badge: "New",
      },
    ],
  },
  {
    title: "Settings",
    items: [
      {
        title: "Preferences",
        href: "/lc-builder/dashboard/settings",
        icon: Settings,
      },
      {
        title: "Help & FAQ",
        href: "/lc-builder/dashboard/help",
        icon: HelpCircle,
      },
    ],
  },
];

export default function LCBuilderLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, signOut, loading: authLoading } = useAuth();
  const [commandOpen, setCommandOpen] = useState(false);

  // Auth check
  useEffect(() => {
    if (!authLoading && !user) {
      navigate("/login?redirect=/lc-builder/dashboard");
    }
  }, [authLoading, user, navigate]);

  // Keyboard shortcut for command palette
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setCommandOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const handleLogout = useCallback(async () => {
    await signOut();
    navigate("/");
  }, [signOut, navigate]);

  const isActive = (href: string) => {
    if (href === "/lc-builder/dashboard") {
      return location.pathname === href;
    }
    return location.pathname.startsWith(href);
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full bg-slate-950">
        {/* Sidebar */}
        <Sidebar className="border-r border-slate-800">
          <SidebarHeader className="border-b border-slate-800 p-4">
            <div className="flex items-center justify-between">
              <Link to="/lc-builder" className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                  <FileText className="w-4 h-4 text-emerald-500" />
                </div>
                <div>
                  <h1 className="font-semibold text-white text-sm">LC Builder</h1>
                  <p className="text-xs text-slate-400">Bank-Ready Applications</p>
                </div>
              </Link>
            </div>
            {/* Search */}
            <button
              onClick={() => setCommandOpen(true)}
              className="mt-4 w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-400 bg-slate-800/50 border border-slate-700 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <Search className="w-4 h-4" />
              <span className="flex-1 text-left">Search...</span>
              <kbd className="text-xs bg-slate-700 px-1.5 py-0.5 rounded">⌘K</kbd>
            </button>
          </SidebarHeader>

          <SidebarContent className="p-2">
            {navItems.map((group) => (
              <SidebarGroup key={group.title}>
                <SidebarGroupLabel className="text-xs text-slate-500 uppercase tracking-wider px-2 mb-1">
                  {group.title}
                </SidebarGroupLabel>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {group.items.map((item) => (
                      <SidebarMenuItem key={item.href}>
                        <SidebarMenuButton
                          asChild
                          isActive={isActive(item.href)}
                          className="w-full"
                        >
                          <Link
                            to={item.href}
                            className={`flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors ${
                              isActive(item.href)
                                ? "bg-emerald-500/10 text-emerald-400"
                                : "text-slate-400 hover:text-white hover:bg-slate-800"
                            }`}
                          >
                            <item.icon className="w-4 h-4" />
                            <span className="text-sm">{item.title}</span>
                          </Link>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    ))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            ))}
          </SidebarContent>

          <SidebarFooter className="border-t border-slate-800 p-4">
            <div className="flex items-center justify-between">
              <Button
                variant="ghost"
                size="sm"
                className="text-slate-400 hover:text-white"
                asChild
              >
                <Link to="/hub">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Hub
                </Link>
              </Button>
            </div>
            {user && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="mt-3 w-full flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-slate-800 transition-colors">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="bg-emerald-500/10 text-emerald-400 text-xs">
                        {user.email?.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 text-left">
                      <p className="text-sm text-white truncate">{user.email}</p>
                      <p className="text-xs text-slate-400">Free Plan</p>
                    </div>
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem asChild>
                    <Link to="/lc-builder/dashboard/settings">
                      <Settings className="w-4 h-4 mr-2" />
                      Settings
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="text-red-400">
                    <LogOut className="w-4 h-4 mr-2" />
                    Sign Out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </SidebarFooter>
        </Sidebar>

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          {/* Mobile Header */}
          <div className="md:hidden flex items-center justify-between p-4 border-b border-slate-800">
            <SidebarTrigger />
            <span className="font-semibold text-white">LC Builder</span>
            <div className="w-8" /> {/* Spacer */}
          </div>
          
          <Outlet />
        </main>
      </div>

      {/* Command Palette */}
      <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
        <CommandInput placeholder="Search applications, clauses, or commands..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Quick Actions">
            <CommandItem
              onSelect={() => {
                setCommandOpen(false);
                navigate("/lc-builder/dashboard/new");
              }}
            >
              <Plus className="w-4 h-4 mr-2" />
              Create New LC Application
            </CommandItem>
            <CommandItem
              onSelect={() => {
                setCommandOpen(false);
                navigate("/lc-builder/dashboard/clauses");
              }}
            >
              <BookOpen className="w-4 h-4 mr-2" />
              Browse Clause Library
            </CommandItem>
          </CommandGroup>
          <CommandGroup heading="Navigation">
            {navItems.flatMap((group) =>
              group.items.map((item) => (
                <CommandItem
                  key={item.href}
                  onSelect={() => {
                    setCommandOpen(false);
                    navigate(item.href);
                  }}
                >
                  <item.icon className="w-4 h-4 mr-2" />
                  {item.title}
                </CommandItem>
              ))
            )}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </SidebarProvider>
  );
}

