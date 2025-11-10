import { useCallback } from "react"
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

import { useCallback } from "react"
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

// Import all auth hooks - they will throw if used outside their providers, which we handle
import { useAdminAuth } from "@/lib/admin/auth"
import { useBankAuth } from "@/lib/bank/auth"
import { useExporterAuth } from "@/lib/exporter/auth"
import { useImporterAuth } from "@/lib/importer/auth"

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

export function UserMenu({ variant = "header" }: UserMenuProps) {
  const navigate = useNavigate()
  const location = useLocation()
  
  // Try to get user from appropriate auth context
  // Only one of these will succeed based on which provider is active
  let user: any = null;
  let logout: (() => void) | null = null;
  let isLoading = false;
  let displayName = "Guest";
  let email = "guest@trdrhub.com";
  let role = "";

  // Try admin auth first
  try {
    const adminAuth = useAdminAuth();
    if (adminAuth?.user) {
      user = adminAuth.user;
      logout = adminAuth.logout;
      isLoading = adminAuth.isLoading;
      displayName = user?.full_name || user?.username || user?.email?.split("@")[0] || "Guest";
      email = user?.email || "guest@trdrhub.com";
      role = user?.role || "";
    }
  } catch (e) {
    // Admin auth not available, try bank auth
    try {
      const bankAuth = useBankAuth();
      if (bankAuth?.user) {
        user = bankAuth.user;
        logout = bankAuth.logout;
        isLoading = bankAuth.isLoading;
        displayName = user?.name || user?.email?.split("@")[0] || "Guest";
        email = user?.email || "guest@trdrhub.com";
        role = user?.role || "";
      }
    } catch (e2) {
      // Bank auth not available, try exporter auth
      try {
        const exporterAuth = useExporterAuth();
        if (exporterAuth?.user) {
          user = exporterAuth.user;
          logout = exporterAuth.logout;
          isLoading = exporterAuth.isLoading;
          displayName = user?.name || user?.email?.split("@")[0] || "Guest";
          email = user?.email || "guest@trdrhub.com";
          role = user?.role || "";
        }
      } catch (e3) {
        // Exporter auth not available, try importer auth
        try {
          const importerAuth = useImporterAuth();
          if (importerAuth?.user) {
            user = importerAuth.user;
            logout = importerAuth.logout;
            isLoading = importerAuth.isLoading;
            displayName = user?.name || user?.email?.split("@")[0] || "Guest";
            email = user?.email || "guest@trdrhub.com";
            role = user?.role || "";
          }
        } catch (e4) {
          // No auth context available
        }
      }
    }
  }

  const initials = getInitials(displayName, email)

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

  if (isLoading || !user) {
    const baseClass = variant === "sidebar"
      ? "flex h-10 w-full animate-pulse items-center justify-start gap-2 rounded-lg bg-muted/50 px-3"
      : "flex h-8 w-32 animate-pulse items-center justify-end gap-2 rounded-full bg-muted/50 px-3"
    return <div className={baseClass} />
  }

  const avatarSeed = encodeURIComponent(email || displayName)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant={variant === "sidebar" ? "outline" : "ghost"}
          className={variant === "sidebar" ? "w-full justify-start gap-3 rounded-lg px-3 py-2" : "flex h-auto items-center gap-2 rounded-full px-2 py-1"}
        >
          <Avatar className="h-8 w-8">
            <AvatarImage
              src={`https://avatar.vercel.sh/${avatarSeed}.svg?size=64`}
              alt={displayName}
            />
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
