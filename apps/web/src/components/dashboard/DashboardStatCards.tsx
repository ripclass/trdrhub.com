/**
 * DashboardStatCards Component
 * 
 * Reusable stat cards for dashboard overview sections.
 */

import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  Clock,
  CreditCard,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { DashboardStats } from "./utils";

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon: React.ReactNode;
  iconBgClass?: string;
  trend?: {
    value: number;
    direction: "up" | "down" | "neutral";
  };
}

/**
 * Individual stat card with icon, value, and optional trend
 */
export function StatCard({
  label,
  value,
  subtext,
  icon,
  iconBgClass = "bg-emerald-500/10",
  trend,
}: StatCardProps) {
  return (
    <Card className="shadow-soft border-0">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{label}</p>
            <p className="text-2xl font-bold text-foreground">{value}</p>
            {subtext && (
              <p className="text-xs text-muted-foreground">{subtext}</p>
            )}
            {trend && (
              <div className="flex items-center gap-1 mt-1">
                <span
                  className={cn(
                    "text-xs font-medium",
                    trend.direction === "up" && "text-green-500",
                    trend.direction === "down" && "text-red-500",
                    trend.direction === "neutral" && "text-muted-foreground"
                  )}
                >
                  {trend.direction === "up" && "↑"}
                  {trend.direction === "down" && "↓"}
                  {trend.value}%
                </span>
                <span className="text-xs text-muted-foreground">vs last month</span>
              </div>
            )}
          </div>
          <div className={cn("p-3 rounded-lg", iconBgClass)}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Standard dashboard stats grid
 */
interface DashboardStatsGridProps {
  stats: DashboardStats;
  variant?: "exporter" | "importer";
}

export function DashboardStatsGrid({ stats, variant = "exporter" }: DashboardStatsGridProps) {
  const accentColor = variant === "exporter" ? "emerald" : "blue";
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard
        label="This Month"
        value={stats.thisMonth}
        subtext={`${stats.totalReviews} total validations`}
        icon={<FileText className={`w-6 h-6 text-${accentColor}-600`} />}
        iconBgClass={`bg-${accentColor}-500/10`}
      />
      
      <StatCard
        label="Success Rate"
        value={`${stats.successRate}%`}
        subtext={variant === "importer" ? "No critical risks" : "No discrepancies"}
        icon={<CheckCircle className="w-6 h-6 text-green-600" />}
        iconBgClass="bg-green-500/10"
      />
      
      <StatCard
        label="Avg. Processing"
        value={stats.avgProcessingTime}
        subtext="Per validation"
        icon={<Clock className="w-6 h-6 text-blue-600" />}
        iconBgClass="bg-blue-500/10"
      />
      
      <StatCard
        label={variant === "importer" ? "Risks Identified" : "Issues Found"}
        value={stats.risksIdentified}
        subtext={`${stats.documentsProcessed} documents processed`}
        icon={<AlertTriangle className="w-6 h-6 text-orange-600" />}
        iconBgClass="bg-orange-500/10"
      />
    </div>
  );
}

/**
 * Usage quota card for billing
 */
interface UsageQuotaCardProps {
  quotaUsed: number;
  quotaLimit: number | null;
}

export function UsageQuotaCard({ quotaUsed, quotaLimit }: UsageQuotaCardProps) {
  const percentage = quotaLimit
    ? Math.min(100, (quotaUsed / quotaLimit) * 100)
    : 0;

  return (
    <Card className="shadow-soft border-0">
      <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-muted-foreground mb-2">Usage Quota</p>
          <div className="space-y-2">
            <p className="text-2xl font-bold text-foreground tabular-nums">
              {quotaUsed.toLocaleString()} / {quotaLimit?.toLocaleString() ?? "∞"}
            </p>
            <Progress value={percentage} className="h-2" />
          </div>
        </div>
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-500/10">
          <TrendingUp className="h-6 w-6 text-blue-500" />
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Pending invoice alert card
 */
interface PendingInvoiceCardProps {
  count: number;
  onViewBilling?: () => void;
}

export function PendingInvoiceCard({ count, onViewBilling }: PendingInvoiceCardProps) {
  if (count === 0) return null;

  return (
    <Card className="shadow-soft border-0 border-yellow-500/20">
      <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-muted-foreground mb-2">Pending Invoice</p>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-bold text-foreground tabular-nums">
              {count}
            </p>
            <Badge variant="outline" className="text-yellow-600 border-yellow-600">
              Action Required
            </Badge>
          </div>
        </div>
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-yellow-500/10">
          <CreditCard className="h-6 w-6 text-yellow-500" />
        </div>
      </CardContent>
    </Card>
  );
}

