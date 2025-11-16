import { useCallback, useMemo, useContext } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Bell, CreditCard, LogOut, User as UserIcon } from "lucide-react"

// Import contexts directly
import { AdminAuthContext } from "@/lib/admin/auth"
import { BankAuthContext } from "@/lib/bank/auth"
import { ExporterAuthContext } from "@/lib/exporter/auth"
import { ImporterAuthContext } from "@/lib/importer/auth"
import { useAuth } from "@/hooks/use-auth"

function getInitials(name?: string | null, email?: string | null) {
  const source = name?.trim() || email?.split("@")[0] || "User"
  const parts = source.split(/\s+/).filter(Boolean)
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase()
  }
  return parts
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase()
}

interface UserMenuProps {
  variant?: "header" | "sidebar"
}

// Helper to safely get context value - useContext doesn't throw, just returns undefined
function useSafeContext<T>(context: React.Context<T | undefined>): T | null {
  const value = useContext(context);
  return value ?? null;
}

export function UserMenu({ variant = "header" }: UserMenuProps) {
  const navigate = useNavigate()
  const location = useLocation()

  // Route flags to scope which auth context should drive the UI
  const isAdminRoute = location.pathname.startsWith("/admin")
  const isBankRoute = location.pathname.includes("/bank-dashboard")
  const isExporterRoute = location.pathname.includes("/exporter-dashboard")
  const isImporterRoute = location.pathname.includes("/importer-dashboard")
  
  // Get main auth first (Supabase-based)
  const mainAuth = useAuth();
  
  // Call all contexts unconditionally (required by React)
  const adminAuth = useSafeContext(AdminAuthContext);
  const bankAuth = useSafeContext(BankAuthContext);
  const exporterAuth = useSafeContext(ExporterAuthContext);
  const importerAuth = useSafeContext(ImporterAuthContext);

  // Determine which auth context to use based on current route
  const activeAuth = useMemo(() => {
    // 1) Admin pages: use admin auth only (never Supabase user)
    if (isAdminRoute) {
      return adminAuth || null
    }

    // 2) Bank dashboard: use bank auth only
    if (isBankRoute) {
      return bankAuth || null
    }

    // 3) SME exporter/importer dashboards: Supabase is the source of truth
    if (isExporterRoute || isImporterRoute) {
      if (mainAuth?.user) {
        return {
          user: mainAuth.user,
          logout: mainAuth.logout,
          isLoading: mainAuth.isLoading,
        }
      }
      // Fallback if any legacy context is still in use
      if (isExporterRoute && exporterAuth?.user) return exporterAuth
      if (isImporterRoute && importerAuth?.user) return importerAuth
      return null
    }

    // 4) Default / other pages: prefer Supabase, else any available context
    if (mainAuth?.user) {
      return {
        user: mainAuth.user,
        logout: mainAuth.logout,
        isLoading: mainAuth.isLoading,
      }
    }

    if (adminAuth?.user) return adminAuth
    if (bankAuth?.user) return bankAuth
    if (exporterAuth?.user) return exporterAuth
    if (importerAuth?.user) return importerAuth

    return null
  }, [
    isAdminRoute,
    isBankRoute,
    isExporterRoute,
    isImporterRoute,
    mainAuth,
    adminAuth,
    bankAuth,
    exporterAuth,
    importerAuth,
  ]);

  const user = activeAuth?.user || null;
  const logout = activeAuth?.logout || null;
  const isLoading = activeAuth?.isLoading || false;
  
  const displayName = useMemo(() => {
    if (!user) return "Guest";
    if ('full_name' in user) return user.full_name || user.username || user.email?.split("@")[0] || "Guest";
    if ('name' in user) return user.name || user.email?.split("@")[0] || "Guest";
    return user.email?.split("@")[0] || "Guest";
  }, [user]);
  
  const email = useMemo(() => {
    if (!user) return "guest@trdrhub.com";
    return user.email || "guest@trdrhub.com";
  }, [user]);
  
  const role = useMemo(() => {
    if (!user) return "";
    return user.role || "";
  }, [user]);

  const initials = getInitials(displayName, email)
  const avatarDataUri = useMemo(() => {
    const safeInitials = initials || "TH"
    const svg = `
      <svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'>
        <rect width='100%' height='100%' rx='12' fill='%230F172A'/>
        <text x='50%' y='52%' dominant-baseline='middle' text-anchor='middle'
          font-family='Inter, Arial, sans-serif' font-size='24' fill='%23FFFFFF'>
          ${safeInitials}
        </text>
      </svg>
    `
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
  }, [initials])

  const handleNavigate = useCallback(
    (section: string) => {
      if (location.pathname.includes('/admin')) {
        if (section === "overview") {
          navigate({ pathname: "/admin" })
        } else {
          const search = new URLSearchParams({ section })
          navigate({ pathname: "/admin", search: `?${search.toString()}` })
        }
      } else if (location.pathname.includes('/bank-dashboard')) {
        navigate(`/lcopilot/bank-dashboard?tab=${section}`)
      } else if (location.pathname.includes('/exporter-dashboard')) {
        navigate(`/lcopilot/exporter-dashboard?section=${section}`)
      } else if (location.pathname.includes('/importer-dashboard')) {
        navigate(`/lcopilot/importer-dashboard?section=${section}`)
      }
    },
    [navigate, location]
  )

  const handleLogout = useCallback(async () => {
    if (!logout) return;
    
    try {
      if (typeof logout === 'function') {
        logout();
      }
    } catch (error) {
      console.error("Failed to log out", error)
    }
  }, [logout])

  if (isLoading) {
    const baseClass = variant === "sidebar"
      ? "flex h-10 w-full animate-pulse items-center justify-start gap-2 rounded-lg bg-muted/50 px-3"
      : "flex h-8 w-32 animate-pulse items-center justify-end gap-2 rounded-full bg-muted/50 px-3"
    return <div className={baseClass} />
  }

  if (!user) {
    // Don't show anything if no user is logged in
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant={variant === "sidebar" ? "outline" : "ghost"}
          className={variant === "sidebar" ? "w-full justify-start gap-3 rounded-lg px-3 py-2" : "flex h-auto items-center gap-2 rounded-full px-2 py-1"}
        >
          <Avatar className="h-8 w-8">
            <AvatarImage src={avatarDataUri} alt={displayName} />
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
          <div className={variant === "sidebar" ? "flex flex-col text-left" : "hidden text-left sm:flex sm:flex-col"}>
            <span className="text-sm font-medium leading-none">{displayName}</span>
            <span className="text-xs text-muted-foreground leading-none">{email}</span>
          </div>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align={variant === "sidebar" ? "start" : "end"} className="w-56" forceMount>
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col gap-1">
            <span className="text-sm font-medium leading-none">{displayName}</span>
            <span className="text-xs text-muted-foreground leading-none">{email}</span>
            {role && (
              <span className="text-xs text-muted-foreground capitalize mt-1">{role}</span>
            )}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => handleNavigate("settings")}> 
          <UserIcon className="mr-2 h-4 w-4" />
          <span>Account</span>
        </DropdownMenuItem>
        {location.pathname.includes('/admin') && (
          <>
            <DropdownMenuItem onSelect={() => handleNavigate("billing-plans")}> 
              <CreditCard className="mr-2 h-4 w-4" />
              <span>Billing</span>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => handleNavigate("system-settings")}> 
              <Bell className="mr-2 h-4 w-4" />
              <span>Notifications</span>
            </DropdownMenuItem>
          </>
        )}
        {(location.pathname.includes('/bank-dashboard') || 
          location.pathname.includes('/exporter-dashboard') || 
          location.pathname.includes('/importer-dashboard')) && (
          <DropdownMenuItem onSelect={() => handleNavigate("billing")}> 
            <CreditCard className="mr-2 h-4 w-4" />
            <span>Billing</span>
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        {logout && (
          <DropdownMenuItem
            onSelect={handleLogout}
            className="text-destructive focus:text-destructive"
          >
            <LogOut className="mr-2 h-4 w-4" />
            <span>Log out</span>
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
