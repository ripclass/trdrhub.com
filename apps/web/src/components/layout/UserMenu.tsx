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
import { useAuth } from "@/hooks/use-auth"
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

export function UserMenu() {
  const navigate = useNavigate()
  const { user, logout, isLoading } = useAuth()

  const displayName = user?.full_name || user?.username || user?.email?.split("@")[0] || "Guest"
  const email = user?.email || "guest@trdrhub.com"
  const initials = getInitials(displayName, email)

  const handleNavigate = useCallback(
    (path: string) => {
      navigate(path)
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

  if (isLoading) {
    return (
      <div className="flex h-8 w-32 animate-pulse items-center justify-end gap-2 rounded-full bg-muted/50 px-3" />
    )
  }

  if (!user) {
    return (
      <Button
        variant="outline"
        size="sm"
        className="rounded-full"
        onClick={() => navigate("/login")}
      >
        Sign in
      </Button>
    )
  }

  const avatarSeed = encodeURIComponent(email || displayName)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="flex h-auto items-center gap-2 rounded-full px-2 py-1"
        >
          <Avatar className="h-8 w-8">
            <AvatarImage
              src={`https://avatar.vercel.sh/${avatarSeed}.svg?size=64`}
              alt={displayName}
            />
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
          <div className="hidden text-left sm:flex sm:flex-col">
            <span className="text-sm font-medium leading-none">{displayName}</span>
            <span className="text-xs text-muted-foreground leading-none">{email}</span>
          </div>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56" forceMount>
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col gap-1">
            <span className="text-sm font-medium leading-none">{displayName}</span>
            <span className="text-xs text-muted-foreground leading-none">{email}</span>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => handleNavigate("/dashboard")}> 
          <UserIcon className="mr-2 h-4 w-4" />
          <span>Account</span>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => handleNavigate("/lcopilot/bank-dashboard/v2?tab=results")}> 
          <CreditCard className="mr-2 h-4 w-4" />
          <span>Billing</span>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => handleNavigate("/lcopilot/bank-dashboard/v2?tab=notifications")}> 
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

