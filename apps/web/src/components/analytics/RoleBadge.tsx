import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { Role } from "@/types/analytics";

interface RoleBadgeProps {
  role: Role;
  dataScope?: string;
  className?: string;
}

const roleConfig = {
  exporter: {
    label: "Exporter",
    variant: "secondary" as const,
    description: "Can view own jobs, upload documents, and see personal analytics"
  },
  importer: {
    label: "Importer",
    variant: "secondary" as const,
    description: "Can view own jobs, upload documents, and see personal analytics"
  },
  bank: {
    label: "Bank",
    variant: "outline" as const,
    description: "Can view system-wide data for compliance monitoring and reporting"
  },
  admin: {
    label: "Admin",
    variant: "default" as const,
    description: "Full system access including user management and system administration"
  }
};

const scopeDescriptions = {
  own: "Viewing your own data",
  "system-wide": "Viewing system-wide data",
  user: "Viewing individual user data"
};

export function RoleBadge({ role, dataScope, className }: RoleBadgeProps) {
  const config = roleConfig[role];

  const tooltipContent = (
    <div className="space-y-2">
      <div className="font-medium">{config.label} Role</div>
      <div className="text-sm text-muted-foreground">
        {config.description}
      </div>
      {dataScope && (
        <div className="text-xs text-muted-foreground border-t pt-2">
          Scope: {scopeDescriptions[dataScope as keyof typeof scopeDescriptions] || dataScope}
        </div>
      )}
    </div>
  );

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant={config.variant}
            className={cn(
              "cursor-help transition-all hover:scale-105",
              className
            )}
          >
            {config.label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          {tooltipContent}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}