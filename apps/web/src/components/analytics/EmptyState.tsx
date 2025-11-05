import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
;
import { BarChart3, FileX, RefreshCw } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

const defaultStates = {
  noData: {
    title: "No data available",
    description: "There's no data for the selected time range and filters.",
    icon: <FileX className="h-12 w-12 text-muted-foreground" />
  },
  noJobs: {
    title: "No jobs found",
    description: "You haven't submitted any validation jobs yet.",
    icon: <BarChart3 className="h-12 w-12 text-muted-foreground" />
  },
  loading: {
    title: "Loading data...",
    description: "Please wait while we fetch your analytics data.",
    icon: <RefreshCw className="h-12 w-12 text-muted-foreground animate-spin" />
  }
};

export function EmptyState({
  title = defaultStates.noData.title,
  description = defaultStates.noData.description,
  icon = defaultStates.noData.icon,
  action,
  className
}: EmptyStateProps) {
  return (
    <Card className={cn("border-dashed", className)}>
      <CardContent className="flex flex-col items-center justify-center py-12">
        <div className="mb-4">
          {icon}
        </div>

        <h3 className="text-lg font-medium text-center mb-2">
          {title}
        </h3>

        <p className="text-sm text-muted-foreground text-center max-w-md mb-6">
          {description}
        </p>

        {action && (
          <Button
            onClick={action.onClick}
            variant="outline"
            size="sm"
          >
            {action.label}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

// Preset components for common states
export function NoDataState({ onRefresh, className }: { onRefresh?: () => void; className?: string }) {
  return (
    <EmptyState
      {...defaultStates.noData}
      action={onRefresh ? { label: "Refresh", onClick: onRefresh } : undefined}
      className={className}
    />
  );
}

export function NoJobsState({ onCreateJob, className }: { onCreateJob?: () => void; className?: string }) {
  return (
    <EmptyState
      {...defaultStates.noJobs}
      action={onCreateJob ? { label: "Create First Job", onClick: onCreateJob } : undefined}
      className={className}
    />
  );
}

export function LoadingState({ className }: { className?: string }) {
  return (
    <EmptyState
      {...defaultStates.loading}
      className={className}
    />
  );
}