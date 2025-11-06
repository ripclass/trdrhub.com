import * as React from "react";

import { cn } from "@/lib/utils";

interface AdminEmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
}

export function AdminEmptyState({
  icon,
  title,
  description,
  action,
  className,
  children,
}: AdminEmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-border/70 bg-muted/10 p-12 text-center",
        className,
      )}
    >
      {icon && <div className="rounded-full bg-muted/40 p-4 text-muted-foreground">{icon}</div>}
      <div className="space-y-1">
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
        {children}
      </div>
      {action}
    </div>
  );
}

