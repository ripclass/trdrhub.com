import { useState, useEffect } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Search,
  Calculator,
  History,
  Upload,
  Globe,
  FileCheck,
  Settings,
  HelpCircle,
  ChevronLeft,
  Menu,
  Star,
  BookOpen,
  Scale,
  TrendingUp,
  LogOut,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/use-auth'
import { useToast } from '@/hooks/use-toast'

interface NavItem {
  title: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string | number
}

interface NavSection {
  title: string
  items: NavItem[]
}

const navSections: NavSection[] = [
  {
    title: 'Classification',
    items: [
      { title: 'Overview', href: '/hs-code/dashboard', icon: TrendingUp },
      { title: 'Classify Product', href: '/hs-code/dashboard/classify', icon: Search },
      { title: 'Search HS Codes', href: '/hs-code/dashboard/search', icon: BookOpen },
      { title: 'Duty Calculator', href: '/hs-code/dashboard/duty', icon: Calculator },
    ],
  },
  {
    title: 'Trade Agreements',
    items: [
      { title: 'FTA Eligibility', href: '/hs-code/dashboard/fta', icon: Globe },
      { title: 'Rules of Origin', href: '/hs-code/dashboard/roo', icon: FileCheck },
      { title: 'Compliance Check', href: '/hs-code/dashboard/compliance', icon: Scale },
    ],
  },
  {
    title: 'History & Bulk',
    items: [
      { title: 'My Classifications', href: '/hs-code/dashboard/history', icon: History },
      { title: 'Favorites', href: '/hs-code/dashboard/favorites', icon: Star },
      { title: 'Bulk Upload', href: '/hs-code/dashboard/bulk', icon: Upload },
    ],
  },
  {
    title: 'Support',
    items: [
      { title: 'Settings', href: '/hs-code/dashboard/settings', icon: Settings },
      { title: 'Help & FAQ', href: '/hs-code/dashboard/help', icon: HelpCircle },
    ],
  },
]

export default function HSCodeLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout, isLoading } = useAuth()
  const { toast } = useToast()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    if (!isLoading && !user) {
      navigate('/login', { state: { from: location.pathname } })
    }
  }, [user, isLoading, navigate, location.pathname])

  const handleLogout = async () => {
    try {
      await logout()
      navigate('/')
      toast({
        title: 'Logged out',
        description: 'You have been successfully logged out.',
      })
    } catch (error) {
      console.error('Logout error:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-emerald-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 flex">
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col bg-slate-900 border-r border-slate-800 transition-all duration-300',
          collapsed ? 'w-16' : 'w-64',
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-slate-800">
          {!collapsed && (
            <Link to="/hub" className="flex items-center gap-2">
              <Search className="h-6 w-6 text-emerald-400" />
              <span className="font-bold text-white">HS Code Finder</span>
            </Link>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed(!collapsed)}
            className="hidden md:flex text-slate-400 hover:text-white"
          >
            <ChevronLeft className={cn('h-5 w-5 transition-transform', collapsed && 'rotate-180')} />
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4">
          {navSections.map((section) => (
            <div key={section.title} className="mb-4">
              {!collapsed && (
                <h3 className="px-4 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  {section.title}
                </h3>
              )}
              <ul className="space-y-1">
                {section.items.map((item) => {
                  const isActive = location.pathname === item.href
                  const Icon = item.icon

                  return (
                    <li key={item.href}>
                      <Link
                        to={item.href}
                        className={cn(
                          'flex items-center gap-3 px-4 py-2 text-sm font-medium rounded-lg mx-2 transition-colors',
                          isActive
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                        )}
                        title={collapsed ? item.title : undefined}
                      >
                        <Icon className="h-5 w-5 flex-shrink-0" />
                        {!collapsed && (
                          <>
                            <span className="flex-1">{item.title}</span>
                            {item.badge && (
                              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-400">
                                {item.badge}
                              </span>
                            )}
                          </>
                        )}
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-slate-800">
          {!collapsed ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                  <span className="text-sm font-medium text-emerald-400">
                    {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {user?.full_name || user?.email || 'User'}
                  </p>
                  <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                className="text-slate-400 hover:text-white"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              className="w-full text-slate-400 hover:text-white"
              title="Logout"
            >
              <LogOut className="h-5 w-5" />
            </Button>
          )}
        </div>
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Main content */}
      <main
        className={cn(
          'flex-1 transition-all duration-300',
          collapsed ? 'md:ml-16' : 'md:ml-64'
        )}
      >
        {/* Mobile header */}
        <div className="md:hidden flex items-center h-16 px-4 border-b border-slate-800 bg-slate-900">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileOpen(true)}
            className="text-slate-400 hover:text-white"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <span className="ml-3 font-bold text-white">HS Code Finder</span>
        </div>

        {/* Page content */}
        <div className="min-h-screen">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

