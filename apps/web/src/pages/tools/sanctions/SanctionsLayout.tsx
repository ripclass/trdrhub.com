import { Link, Outlet, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import {
  LayoutDashboard,
  Search,
  Ship,
  Package,
  History,
  FileCheck,
  Settings,
  HelpCircle,
  Shield,
  Users,
  Bell,
  LogOut,
  ChevronRight,
  Upload,
  Key,
} from "lucide-react";

const navigation = [
  { name: "Overview", href: "/sanctions/dashboard", icon: LayoutDashboard },
  { name: "Screen Party", href: "/sanctions/dashboard/screen/party", icon: Users },
  { name: "Screen Vessel", href: "/sanctions/dashboard/screen/vessel", icon: Ship },
  { name: "Screen Goods", href: "/sanctions/dashboard/screen/goods", icon: Package },
  { divider: true },
  { name: "Batch Upload", href: "/sanctions/dashboard/batch", icon: Upload },
  { name: "History", href: "/sanctions/dashboard/history", icon: History },
  { name: "Certificates", href: "/sanctions/dashboard/certificates", icon: FileCheck },
  { name: "Watchlist", href: "/sanctions/dashboard/watchlist", icon: Bell },
  { divider: true },
  { name: "API Access", href: "/sanctions/dashboard/api", icon: Key },
  { name: "Settings", href: "/sanctions/dashboard/settings", icon: Settings },
  { name: "Help & FAQ", href: "/sanctions/dashboard/help", icon: HelpCircle },
];

export default function SanctionsLayout() {
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      <TRDRHeader />

      <div className="flex-1 flex">
        {/* Sidebar */}
        <aside className="w-64 bg-slate-900/50 border-r border-slate-800 flex flex-col">
          {/* Tool Header */}
          <div className="p-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center">
                <Shield className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h2 className="font-semibold text-white">Sanctions Screener</h2>
                <p className="text-xs text-slate-500">Compliance Tool</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
            {navigation.map((item, idx) =>
              item.divider ? (
                <div key={idx} className="my-2 border-t border-slate-800" />
              ) : (
                <Link
                  key={item.name}
                  to={item.href!}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    location.pathname === item.href
                      ? "bg-red-500/10 text-red-400 border border-red-500/20"
                      : "text-slate-400 hover:text-white hover:bg-slate-800/50"
                  )}
                >
                  {item.icon && <item.icon className="w-4 h-4" />}
                  {item.name}
                  {location.pathname === item.href && (
                    <ChevronRight className="w-4 h-4 ml-auto" />
                  )}
                </Link>
              )
            )}
          </nav>

          {/* User Section */}
          {user && (
            <div className="p-3 border-t border-slate-800">
              <div className="flex items-center gap-3 px-3 py-2">
                <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
                  <span className="text-xs font-medium text-white">
                    {user.email?.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {user.email}
                  </p>
                  <p className="text-xs text-slate-500">Free tier</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-slate-500 hover:text-white"
                  onClick={() => logout()}
                >
                  <LogOut className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>

      <TRDRFooter />
    </div>
  );
}

