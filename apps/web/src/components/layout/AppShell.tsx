import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { Separator } from '@/components/ui/separator';
import { UserMenu } from '@/components/layout/UserMenu';

// Inline cn function to avoid import/bundling issues
// This is a simplified version that handles the most common cases
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

interface AppShellProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  breadcrumbs?: { label: string; href?: string }[];
  toolbar?: ReactNode;
  compact?: boolean;
}

export function AppShell({
  children,
  title,
  subtitle,
  actions,
  breadcrumbs,
  toolbar,
  compact = false,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-background" data-app-shell="true">
      {/* Top Bar */}
      <header className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
        <div className="container flex h-14 items-center justify-between px-4">
          {/* Left: Breadcrumbs */}
          {breadcrumbs && breadcrumbs.length > 0 && (
            <div className="flex items-center gap-2 text-sm">
              {breadcrumbs.map((crumb, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  {idx > 0 && <span className="text-muted-foreground">/</span>}
                  {crumb.href ? (
                    <Link
                      to={crumb.href}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="text-foreground font-medium">{crumb.label}</span>
                  )}
                </div>
              ))}
            </div>
          )}
          
          {/* Right: Theme Toggle */}
          <div className="ml-auto flex items-center gap-2">
            <UserMenu />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Page Header */}
      {(title || subtitle || actions) && (
        <div className={cn(
          "border-b bg-muted/30",
          compact ? "py-3" : "py-4"
        )}>
          <div className="container px-4">
            <div className="flex items-start justify-between gap-4">
              {/* Title & Subtitle */}
              <div className="space-y-1">
                {title && (
                  <h1 className={cn(
                    "font-semibold tracking-tight",
                    compact ? "text-lg" : "text-xl"
                  )}>
                    {title}
                  </h1>
                )}
                {subtitle && (
                  <p className="text-sm text-muted-foreground">{subtitle}</p>
                )}
              </div>
              
              {/* Actions */}
              {actions && (
                <div className="flex items-center gap-2 shrink-0">
                  {actions}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Toolbar */}
      {toolbar && (
        <>
          <div className={cn(
            "bg-muted/20",
            compact ? "py-2" : "py-3"
          )}>
            <div className="container px-4">
              {toolbar}
            </div>
          </div>
          <Separator />
        </>
      )}

      {/* Main Content */}
      <main className={cn(
        "container",
        compact ? "py-4 px-4" : "py-6 px-4"
      )}>
        {children}
      </main>
    </div>
  );
}

// Toolbar Components for consistent styling
export function AppShellToolbar({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("flex items-center gap-3 flex-wrap", className)}>
      {children}
    </div>
  );
}

export function AppShellToolbarSection({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      {children}
    </div>
  );
}

