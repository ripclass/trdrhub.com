import { useCallback } from "react"
import { useNavigate } from "react-router-dom"
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
import { useAdminAuth } from "@/lib/admin/auth"
import type { AdminSection } from "@/lib/admin/types"
import { Bell, CreditCard, LogOut, User as UserIcon } from "lucide-react"

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
  const { user, logout, isLoading } = useAdminAuth()

  const displayName = user?.full_name || user?.username || user?.email?.split("@")[0] || "Guest"
  const email = user?.email || "guest@trdrhub.com"
  const initials = getInitials(displayName, email)

  const handleNavigate = useCallback(
    (section: AdminSection | "overview") => {
      if (section === "overview") {
        navigate({ pathname: "/admin" })
      } else {
        const search = new URLSearchParams({ section })
        navigate({ pathname: "/admin", search: `?${search.toString()}` })
      }
    },
    [navigate]
  )

  const handleLogout = useCallback(async () => {
    try {
      await logout()
    } catch (error) {
      console.error("Failed to log out", error)
    } finally {
      navigate("/login")
    }
  }, [logout, navigate])

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
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => handleNavigate("overview")}> 
          <UserIcon className="mr-2 h-4 w-4" />
          <span>Account</span>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => handleNavigate("billing-plans")}> 
          <CreditCard className="mr-2 h-4 w-4" />
          <span>Billing</span>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => handleNavigate("system-settings")}> 
          <Bell className="mr-2 h-4 w-4" />
          <span>Notifications</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={handleLogout}
          className="text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>Log out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

