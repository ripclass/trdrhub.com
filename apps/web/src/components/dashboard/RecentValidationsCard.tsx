/**
 * RecentValidationsCard Component
 * 
 * Displays recent validation history in a card format.
 * Used by both Exporter and Importer dashboards.
 */

import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { ArrowRight, FileText } from "lucide-react";
import type { HistoryItem } from "./utils";

interface RecentValidationsCardProps {
  history: HistoryItem[];
  variant?: "exporter" | "importer";
  onViewAll?: () => void;
  emptyMessage?: string;
}

export function RecentValidationsCard({
  history,
  variant = "exporter",
  onViewAll,
  emptyMessage = "No recent validations. Upload your first LC to get started.",
}: RecentValidationsCardProps) {
  const navigate = useNavigate();
  
  const handleViewAll = () => {
    if (onViewAll) {
      onViewAll();
    } else {
      const basePath = variant === "exporter" 
        ? "/lcopilot/exporter-dashboard"
        : "/lcopilot/importer-dashboard";
      navigate(`${basePath}?section=reviews`);
    }
  };

  return (
    <Card className="shadow-soft border-0">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle className="text-lg font-semibold">Recent Validations</CardTitle>
          <CardDescription>Your latest LC reviews</CardDescription>
        </div>
        <Button variant="ghost" size="sm" onClick={handleViewAll}>
          View All
          <ArrowRight className="w-4 h-4 ml-1" />
        </Button>
      </CardHeader>
      <CardContent>
        {history.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">{emptyMessage}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {history.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between py-3 border-b border-border/50 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                    <FileText className="w-5 h-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">{item.party}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.type} • {item.date}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {item.risks > 0 && (
                    <span className="text-xs text-muted-foreground">
                      {item.risks} {item.risks === 1 ? "issue" : "issues"}
                    </span>
                  )}
                  <StatusBadge 
                    status={item.status === "approved" ? "success" : item.status === "flagged" ? "warning" : "info"} 
                    label={item.status === "approved" ? "Passed" : item.status === "flagged" ? "Issues" : "Pending"}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

