/**
 * Doc Generator Dashboard Layout
 * 
 * Sidebar layout for the document generator tool.
 */

import { useState, useCallback } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import {
  FileText,
  Plus,
  FolderOpen,
  FileCheck,
  Settings,
  HelpCircle,
  ArrowLeft,
  Search,
  ChevronDown,
  LogOut,
  Package,
  Palette,
  Scroll,
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
    title: "Documents",
    items: [
      {
        title: "All Documents",
        href: "/doc-generator/dashboard",
        icon: FolderOpen,
      },
      {
        title: "Create New",
        href: "/doc-generator/dashboard/new",
        icon: Plus,
      },
    ],
  },
  {
    title: "Document Types",
    items: [
      {
        title: "Commercial Invoice",
        href: "/doc-generator/dashboard?type=commercial_invoice",
        icon: FileText,
      },
      {
        title: "Packing List",
        href: "/doc-generator/dashboard?type=packing_list",
        icon: Package,
      },
      {
        title: "Beneficiary Cert",
        href: "/doc-generator/dashboard?type=beneficiary_certificate",
        icon: FileCheck,
      },
      {
        title: "Certificate of Origin",
        href: "/doc-generator/dashboard?type=certificate_of_origin",
        icon: Scroll,
      },
    ],
  },
  {
    title: "Settings",
    items: [
      {
        title: "Company Branding",
        href: "/doc-generator/dashboard/branding",
        icon: Palette,
      },
      {
        title: "Preferences",
        href: "/doc-generator/dashboard/settings",
        icon: Settings,
      },
      {
        title: "Help",
        href: "/doc-generator/dashboard/help",
        icon: HelpCircle,
      },
    ],
  },
];

export default function DocGeneratorLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [commandOpen, setCommandOpen] = useState(false);

  // Get user initials
  const initials = user?.email
    ?.split("@")[0]
    ?.slice(0, 2)
    ?.toUpperCase() || "DG";

  const handleLogout = useCallback(() => {
    logout().then(() => {
      window.location.href = "/login";
    });
  }, [logout]);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-slate-950">
        {/* Sidebar */}
        <Sidebar className="border-r border-slate-800">
          <SidebarHeader className="border-b border-slate-800 p-4">
            <Link to="/hub" className="flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-3">
              <ArrowLeft className="w-4 h-4" />
              Back to Hub
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-white font-semibold">Doc Generator</h2>
                <p className="text-xs text-slate-500">Shipping Documents</p>
              </div>
            </div>
          </SidebarHeader>

          <SidebarContent>
            {navItems.map((group) => (
              <SidebarGroup key={group.title}>
                <SidebarGroupLabel className="text-slate-500">{group.title}</SidebarGroupLabel>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {group.items.map((item) => {
                      const isActive = location.pathname === item.href ||
                        (item.href.includes("?") && location.pathname + location.search === item.href);
                      return (
                        <SidebarMenuItem key={item.title}>
                          <SidebarMenuButton
                            asChild
                            isActive={isActive}
                            className="text-slate-400 hover:text-white hover:bg-slate-800"
                          >
                            <Link to={item.href}>
                              <item.icon className="w-4 h-4" />
                              <span>{item.title}</span>
                            </Link>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      );
                    })}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            ))}
          </SidebarContent>

          <SidebarFooter className="border-t border-slate-800 p-4">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="w-full justify-start gap-2 text-slate-400 hover:text-white">
                  <Avatar className="w-6 h-6">
                    <AvatarFallback className="bg-blue-600 text-white text-xs">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-sm truncate flex-1 text-left">
                    {user?.email || "User"}
                  </span>
                  <ChevronDown className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56">
                <DropdownMenuItem asChild>
                  <Link to="/hub/settings">Settings</Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-red-500">
                  <LogOut className="w-4 h-4 mr-2" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarFooter>
        </Sidebar>

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <SidebarTrigger className="text-slate-400 hover:text-white" />
              <h1 className="text-lg font-semibold text-white">Document Generator</h1>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="border-slate-700 text-slate-400"
              onClick={() => setCommandOpen(true)}
            >
              <Search className="w-4 h-4 mr-2" />
              Search
              <kbd className="ml-2 text-xs bg-slate-800 px-1.5 py-0.5 rounded">⌘K</kbd>
            </Button>
          </div>
          <Outlet />
        </main>

        {/* Command palette */}
        <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
          <CommandInput placeholder="Search documents..." />
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            <CommandGroup heading="Actions">
              <CommandItem onSelect={() => { navigate("/doc-generator/dashboard/new"); setCommandOpen(false); }}>
                <Plus className="w-4 h-4 mr-2" />
                Create New Document Set
              </CommandItem>
              <CommandItem onSelect={() => { navigate("/doc-generator/dashboard"); setCommandOpen(false); }}>
                <FolderOpen className="w-4 h-4 mr-2" />
                View All Documents
              </CommandItem>
            </CommandGroup>
          </CommandList>
        </CommandDialog>
      </div>
    </SidebarProvider>
  );
}

