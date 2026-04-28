import { ReactNode } from "react";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { UserMenu } from "@/components/layout/UserMenu";
import { EnvironmentBanner } from "@/components/shared/EnvironmentBanner";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { GlobalSearchBar } from "@/components/search/GlobalSearchBar";

// Inline cn function to avoid import/bundling issues
function cn(...classes: (string | undefined | null | boolean | Record<string, boolean>)[]): string {
  return classes
    .filter(Boolean)
    .map((cls) => {
      if (typeof cls === 'string') return cls;
      if (typeof cls === 'object' && cls !== null) {
        return Object.entries(cls)
          .filter(([_, val]) => val)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join(' ');
}

interface DashboardLayoutProps {
  sidebar: ReactNode;
  title?: string;
  breadcrumbs?: { label: string; href?: string }[];
  actions?: ReactNode;
  topbar?: ReactNode; // Slot for topbar content (mode toggle, search, etc.)
  workspaceSwitcher?: ReactNode; // Multi-activity header switcher — renders null when not applicable
  headerExtras?: ReactNode; // Additional header controls (tier-gated links, etc.) — self-hide when N/A
  children: ReactNode;
}

export function DashboardLayout({
  sidebar,
  title,
  breadcrumbs,
  actions,
  topbar,
  workspaceSwitcher,
  headerExtras,
  children,
}: DashboardLayoutProps) {
  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "16rem",
          "--header-height": "3.5rem",
        } as React.CSSProperties
      }
    >
      {sidebar}
      <SidebarInset>
        {/* Header */}
        <header className="flex h-[var(--header-height)] shrink-0 items-center gap-2 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 sticky top-0 z-50">
          <div className="flex w-full items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            
            {/* Breadcrumbs */}
            {breadcrumbs && breadcrumbs.length > 0 && (
              <div className="flex items-center gap-2 text-sm">
                {breadcrumbs.map((crumb, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    {idx > 0 && <span className="text-muted-foreground">/</span>}
                    {crumb.href ? (
                      <a
                        href={crumb.href}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {crumb.label}
                      </a>
                    ) : (
                      <span className="text-foreground font-medium">{crumb.label}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {/* Title (if no breadcrumbs) */}
            {!breadcrumbs && title && (
              <h1 className="text-base font-medium">{title}</h1>
            )}

            {/* Workspace switcher — multi-activity companies only */}
            {workspaceSwitcher && (
              <div className="ml-3 flex items-center">
                {workspaceSwitcher}
              </div>
            )}

            {/* Header extras (enterprise-tier Group overview link, etc.) */}
            {headerExtras && (
              <div className="ml-2 flex items-center">
                {headerExtras}
              </div>
            )}

            {/* Topbar content (mode toggle, search, etc.) */}
            {topbar && (
              <div className="flex-1 flex items-center justify-center">
                {topbar}
              </div>
            )}

            {/* Global search — Phase A12. Hidden on small screens. */}
            <div className={`${topbar ? "ml-2" : "ml-auto"} hidden md:flex items-center min-w-[280px]`}>
              <GlobalSearchBar />
            </div>

            {/* Actions */}
            <div className="ml-auto flex items-center gap-2">
              {actions}
              <NotificationBell />
              <UserMenu />
              <ThemeToggle />
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex flex-1 flex-col">
          <EnvironmentBanner />
          <div className="pt-6">
            {children}
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

