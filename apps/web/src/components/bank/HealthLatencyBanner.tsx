/**
 * Health/Latency Banner Component
 * Shows system health status and latency metrics in a banner at the top of Bank Dashboard
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Activity, AlertCircle, CheckCircle2, Clock } from "lucide-react";

interface HealthStatus {
  status: "healthy" | "degraded" | "down";
  latency: number; // milliseconds
  uptime: number; // percentage
  lastChecked: string;
  message?: string;
}

const HEALTH_COLORS = {
  healthy: "bg-green-500/10 border-green-500/20 text-green-700 dark:text-green-400",
  degraded: "bg-yellow-500/10 border-yellow-500/20 text-yellow-700 dark:text-yellow-400",
  down: "bg-red-500/10 border-red-500/20 text-red-700 dark:text-red-400",
};

const STATUS_ICONS = {
  healthy: CheckCircle2,
  degraded: AlertCircle,
  down: AlertCircle,
};

// Mock API - replace with real endpoint
async function fetchHealthStatus(): Promise<HealthStatus> {
  // Simulate API call
  await new Promise((resolve) => setTimeout(resolve, 500));
  
  // Mock data - in real app, call: GET /api/health
  return {
    status: "healthy",
    latency: 45,
    uptime: 99.9,
    lastChecked: new Date().toISOString(),
  };
}

export function HealthLatencyBanner() {
  const { data: health, isLoading } = useQuery({
    queryKey: ["health-status"],
    queryFn: fetchHealthStatus,
    refetchInterval: 30000, // Check every 30 seconds
  });

  if (isLoading || !health) {
    return null;
  }

  const StatusIcon = STATUS_ICONS[health.status];
  const statusColor = HEALTH_COLORS[health.status];

  return (
    <Alert className={`${statusColor} border mb-4`}>
      <div className="flex items-center justify-between w-full">
        <div className="flex items-center gap-3">
          <StatusIcon className="h-4 w-4" />
          <div className="flex items-center gap-4">
            <div>
              <span className="font-medium">System Status: </span>
              <Badge variant="outline" className="ml-1">
                {health.status === "healthy" ? "Operational" : health.status === "degraded" ? "Degraded" : "Down"}
              </Badge>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span className="text-sm">Latency: {health.latency}ms</span>
            </div>
            <div className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              <span className="text-sm">Uptime: {health.uptime}%</span>
            </div>
          </div>
        </div>
        {health.message && (
          <AlertDescription className="text-sm">{health.message}</AlertDescription>
        )}
      </div>
    </Alert>
  );
}

