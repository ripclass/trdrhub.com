import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { FileText, CheckCircle, AlertTriangle, TrendingUp } from "lucide-react";
import { bankApi } from "@/api/bank";

interface QuickStats {
  todayCount: number;
  avgScore: number;
  totalDiscrepancies: number;
  processingTime: string;
}

export function BankQuickStats() {
  const [stats, setStats] = useState<QuickStats>({
    todayCount: 0,
    avgScore: 0,
    totalDiscrepancies: 0,
    processingTime: "0m",
  });

  // Fetch today's results
  const { data: resultsData } = useQuery({
    queryKey: ['bank-stats'],
    queryFn: () => {
      const today = new Date();
      const startOfDay = new Date(today);
      startOfDay.setHours(0, 0, 0, 0);
      
      return bankApi.getResults({
        start_date: startOfDay.toISOString(),
        end_date: today.toISOString(),
        limit: 1000,
      });
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  useEffect(() => {
    if (resultsData?.results) {
      const todayResults = resultsData.results;
      
      const avgScore =
        todayResults.length > 0
          ? Math.round(
              todayResults.reduce((sum, r) => sum + r.compliance_score, 0) /
                todayResults.length
            )
          : 0;

      const totalDiscrepancies = todayResults.reduce(
        (sum, r) => sum + r.discrepancy_count,
        0
      );

      setStats({
        todayCount: todayResults.length,
        avgScore,
        totalDiscrepancies,
        processingTime: "2.3m", // TODO: Calculate from actual processing times
      });
    }
  }, [resultsData]);

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card className="overflow-hidden">
        <CardContent className="p-6 pt-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-muted-foreground mb-2">Today's Validations</p>
              <p className="text-2xl font-bold text-foreground tabular-nums">
                {stats.todayCount}
              </p>
            </div>
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <FileText className="h-6 w-6 text-primary" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardContent className="p-6 pt-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-muted-foreground mb-2">Average Score</p>
              <p className="text-2xl font-bold text-foreground tabular-nums">
                {stats.avgScore}%
              </p>
            </div>
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-green-500/10">
              <TrendingUp className="h-6 w-6 text-green-500" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardContent className="p-6 pt-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-muted-foreground mb-2">Total Discrepancies</p>
              <p className="text-2xl font-bold text-foreground tabular-nums">
                {stats.totalDiscrepancies}
              </p>
            </div>
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-yellow-500/10">
              <AlertTriangle className="h-6 w-6 text-yellow-500" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardContent className="p-6 pt-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-muted-foreground mb-2">Avg Processing Time</p>
              <p className="text-2xl font-bold text-foreground tabular-nums">
                {stats.processingTime}
              </p>
            </div>
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-500/10">
              <CheckCircle className="h-6 w-6 text-blue-500" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
