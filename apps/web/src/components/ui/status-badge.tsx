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
import { CheckCircle, XCircle, AlertCircle, Clock } from "lucide-react";

export interface StatusBadgeProps {
  status: "success" | "error" | "warning" | "pending";
  children: React.ReactNode;
  className?: string;
}

const statusConfig = {
  success: {
    className: "bg-success/10 text-success border-success/20",
    icon: CheckCircle,
  },
  error: {
    className: "bg-destructive/10 text-destructive border-destructive/20",
    icon: XCircle,
  },
  warning: {
    className: "bg-warning/10 text-warning border-warning/20",
    icon: AlertCircle,
  },
  pending: {
    className: "bg-info/10 text-info border-info/20",
    icon: Clock,
  },
};

export function StatusBadge({ status, children, className }: StatusBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border",
        config.className,
        className
      )}
    >
      <Icon className="w-3 h-3" />
      {children}
    </span>
  );
}