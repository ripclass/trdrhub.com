import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ArrowDownIcon, ArrowUpIcon, TrendingUpIcon, TrendingDownIcon } from "lucide-react";
import type { KpiCardProps } from "@/types/analytics";

export function KpiCard({
  title,
  value,
  change,
  changeType,
  description,
  icon,
  className
}: KpiCardProps) {
  const formatValue = (val: string | number): string => {
    if (typeof val === 'number') {
      if (val >= 1000000) {
        return `${(val / 1000000).toFixed(1)}M`;
      } else if (val >= 1000) {
        return `${(val / 1000).toFixed(1)}K`;
      }
      return val.toLocaleString();
    }
    return val;
  };

  const getChangeColor = (type?: "increase" | "decrease") => {
    if (!type || !change) return "text-muted-foreground";

    // For most metrics, increase is good, decrease is bad
    // But for rejection rate, decrease is good, increase is bad
    const isRejectionRate = title.toLowerCase().includes('rejection');

    if (isRejectionRate) {
      return type === "decrease" ? "text-green-600" : "text-red-600";
    } else {
      return type === "increase" ? "text-green-600" : "text-red-600";
    }
  };

  const getChangeIcon = (type?: "increase" | "decrease") => {
    if (!type || !change) return null;

    const isRejectionRate = title.toLowerCase().includes('rejection');
    const IconComponent = type === "increase" ? ArrowUpIcon : ArrowDownIcon;
    const TrendIcon = type === "increase" ? TrendingUpIcon : TrendingDownIcon;

    return (
      <div className="flex items-center gap-1">
        <IconComponent className="h-3 w-3" />
        <TrendIcon className="h-3 w-3" />
      </div>
    );
  };

  return (
    <Card className={cn("transition-all hover:shadow-md", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {icon && (
          <div className="h-4 w-4 text-muted-foreground">
            {icon}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {formatValue(value)}
        </div>

        {(change !== undefined || description) && (
          <div className="flex items-center justify-between mt-2">
            {change !== undefined && (
              <div className={cn(
                "flex items-center text-xs font-medium",
                getChangeColor(changeType)
              )}>
                {getChangeIcon(changeType)}
                <span className="ml-1">
                  {Math.abs(change).toFixed(1)}%
                </span>
              </div>
            )}

            {description && (
              <CardDescription className="text-xs">
                {description}
              </CardDescription>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}