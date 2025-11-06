import * as React from "react";

import { cn } from "@/lib/utils";

interface AdminToolbarProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  children?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export function AdminToolbar({
  title,
  description,
  children,
  actions,
  className,
}: AdminToolbarProps) {
  return (
    <div className={cn("flex flex-col gap-4 border-b border-border/60 bg-gradient-to-br from-background to-muted/30 p-6", className)}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight text-foreground">{title}</h1>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-3">{children}</div>}
    </div>
  );
}

