import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { useAuth } from "@/hooks/use-auth"
import { useNavigate } from "react-router-dom"
import {
  LayoutDashboard,
  Users,
  Building2,
  GitBranch,
  BarChart3,
  Bell,
  Settings,
  HelpCircle,
  LogOut,
  ShieldCheck,
  Layers,
  FileText,
  TrendingUp,
} from "lucide-react"

type Section =
  | "dashboard"
  | "workspaces"
  | "teams"
  | "analytics"
  | "governance"
  | "notifications"
  | "settings"
  | "help"

interface EnterpriseSidebarProps {
  activeSection: Section
  onSectionChange: (section: Section) => void
  user?: {
    id: string
    name: string
    email: string
    role: string
  } | null
}

export function EnterpriseSidebar({ activeSection, onSectionChange, user }: EnterpriseSidebarProps) {
  const { logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate("/login")
  }

  const navItems = [
    {
      id: "dashboard" as Section,
      label: "Dashboard",
      icon: LayoutDashboard,
      description: "Overview & insights",
    },
    {
      id: "workspaces" as Section,
      label: "Workspaces",
      icon: Layers,
      description: "Export, Import, Finance",
    },
    {
      id: "teams" as Section,
      label: "Team Management",
      icon: Users,
      description: "Roles & permissions",
    },
    {
      id: "analytics" as Section,
      label: "Analytics",
      icon: BarChart3,
      description: "Cross-team reports",
    },
    {
      id: "governance" as Section,
      label: "Governance",
      icon: ShieldCheck,
      description: "Policies & controls",
    },
  ]

  const secondaryItems = [
    { id: "notifications" as Section, label: "Notifications", icon: Bell },
    { id: "settings" as Section, label: "Settings", icon: Settings },
    { id: "help" as Section, label: "Help & Support", icon: HelpCircle },
  ]

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card">
      {/* Header */}
      <div className="flex h-16 items-center gap-3 border-b px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Building2 className="h-6 w-6 text-primary" />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold">LCopilot</span>
          <span className="text-xs text-muted-foreground">Enterprise</span>
        </div>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 px-3 py-4">
        <div className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activeSection === item.id
            return (
              <Button
                key={item.id}
                variant={isActive ? "secondary" : "ghost"}
                className={`w-full justify-start gap-3 ${
                  isActive ? "bg-secondary" : "hover:bg-secondary/50"
                }`}
                onClick={() => onSectionChange(item.id)}
              >
                <Icon className="h-4 w-4" />
                <div className="flex flex-col items-start gap-0">
                  <span className="text-sm font-medium">{item.label}</span>
                  {item.description && (
                    <span className="text-xs text-muted-foreground">{item.description}</span>
                  )}
                </div>
              </Button>
            )
          })}
        </div>

        <Separator className="my-4" />

        <div className="space-y-1">
          {secondaryItems.map((item) => {
            const Icon = item.icon
            const isActive = activeSection === item.id
            return (
              <Button
                key={item.id}
                variant={isActive ? "secondary" : "ghost"}
                className={`w-full justify-start gap-3 ${
                  isActive ? "bg-secondary" : "hover:bg-secondary/50"
                }`}
                onClick={() => onSectionChange(item.id)}
              >
                <Icon className="h-4 w-4" />
                <span className="text-sm">{item.label}</span>
              </Button>
            )
          })}
        </div>
      </ScrollArea>

      {/* User Section */}
      <div className="border-t p-4">
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
            {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || "U"}
          </div>
          <div className="flex flex-1 flex-col overflow-hidden">
            <div className="truncate text-sm font-medium">{user?.name || user?.email?.split("@")[0] || "User"}</div>
            <div className="flex items-center gap-1">
              <Badge variant="secondary" className="text-xs">
                Tenant Admin
              </Badge>
            </div>
          </div>
        </div>
        <Button variant="outline" size="sm" className="w-full gap-2" onClick={handleLogout}>
          <LogOut className="h-4 w-4" />
          <span>Sign out</span>
        </Button>
      </div>
    </div>
  )
}

