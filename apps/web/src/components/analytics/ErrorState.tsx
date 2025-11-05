import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { AlertTriangle, RefreshCw, ShieldX, Wifi } from "lucide-react";

interface ErrorStateProps {
  error: Error | string;
  onRetry?: () => void;
  className?: string;
}

interface ErrorConfig {
  title: string;
  description: string;
  icon: React.ReactNode;
  variant: "default" | "destructive";
}

const getErrorConfig = (error: Error | string): ErrorConfig => {
  const errorMessage = typeof error === 'string' ? error : error.message;
  const lowerError = errorMessage.toLowerCase();

  if (lowerError.includes('permission') || lowerError.includes('403')) {
    return {
      title: "Access Denied",
      description: "You don't have permission to view this data. Contact your administrator if you believe this is an error.",
      icon: <ShieldX className="h-12 w-12 text-destructive" />,
      variant: "destructive"
    };
  }

  if (lowerError.includes('network') || lowerError.includes('fetch')) {
    return {
      title: "Connection Error",
      description: "Unable to connect to the server. Please check your internet connection and try again.",
      icon: <Wifi className="h-12 w-12 text-muted-foreground" />,
      variant: "default"
    };
  }

  if (lowerError.includes('timeout')) {
    return {
      title: "Request Timeout",
      description: "The request took too long to complete. Please try again.",
      icon: <AlertTriangle className="h-12 w-12 text-muted-foreground" />,
      variant: "default"
    };
  }

  return {
    title: "Something went wrong",
    description: errorMessage || "An unexpected error occurred while loading the data.",
    icon: <AlertTriangle className="h-12 w-12 text-destructive" />,
    variant: "destructive"
  };
};

export function ErrorState({ error, onRetry, className }: ErrorStateProps) {
  const config = getErrorConfig(error);

  return (
    <Card className={cn("border-dashed", className)}>
      <CardContent className="flex flex-col items-center justify-center py-12">
        <div className="mb-4">
          {config.icon}
        </div>

        <h3 className="text-lg font-medium text-center mb-2">
          {config.title}
        </h3>

        <p className="text-sm text-muted-foreground text-center max-w-md mb-6">
          {config.description}
        </p>

        {onRetry && (
          <Button
            onClick={onRetry}
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

// Specific error components
export function PermissionError({ className }: { className?: string }) {
  return (
    <Alert variant="destructive" className={className}>
      <ShieldX className="h-4 w-4" />
      <AlertDescription>
        You don't have permission to view this analytics data. Your current role only allows access to your own data.
      </AlertDescription>
    </Alert>
  );
}

export function NetworkError({ onRetry, className }: { onRetry?: () => void; className?: string }) {
  return (
    <ErrorState
      error="Unable to load analytics data. Please check your connection and try again."
      onRetry={onRetry}
      className={className}
    />
  );
}

export function TimeoutError({ onRetry, className }: { onRetry?: () => void; className?: string }) {
  return (
    <ErrorState
      error="The request timed out while loading analytics data."
      onRetry={onRetry}
      className={className}
    />
  );
}