/**
 * DashboardLoading Component
 * 
 * Full-page loading spinner for dashboard auth checks.
 */

import { cn } from "@/lib/utils";

interface DashboardLoadingProps {
  message?: string;
  variant?: "exporter" | "importer";
}

export function DashboardLoading({
  message = "Loading...",
  variant = "exporter",
}: DashboardLoadingProps) {
  const spinnerColor = variant === "exporter" ? "border-emerald-500" : "border-blue-500";
  
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div
          className={cn(
            "w-8 h-8 border-4 border-t-transparent rounded-full animate-spin mx-auto mb-4",
            spinnerColor
          )}
        />
        <p className="text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}

