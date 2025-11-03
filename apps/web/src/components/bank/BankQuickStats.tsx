import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { FileText, CheckCircle, AlertTriangle, TrendingUp } from "lucide-react";

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

  useEffect(() => {
    // Load stats from localStorage (temporary until backend is ready)
    const loadStats = () => {
      const stored = localStorage.getItem("bank_validation_results");
      if (stored) {
        try {
          const results = JSON.parse(stored);
          const today = new Date();
          today.setHours(0, 0, 0, 0);

          const todayResults = results.filter((r: any) => {
            const completedAt = new Date(r.completedAt);
            return completedAt >= today;
          });

          const allResults = results.map((r: any) => ({
            complianceScore: r.complianceScore || 0,
            discrepancyCount: r.discrepancyCount || 0,
          }));

          const avgScore =
            allResults.length > 0
              ? Math.round(
                  allResults.reduce((sum: number, r: any) => sum + r.complianceScore, 0) /
                    allResults.length
                )
              : 0;

          const totalDiscrepancies = allResults.reduce(
            (sum: number, r: any) => sum + r.discrepancyCount,
            0
          );

          setStats({
            todayCount: todayResults.length,
            avgScore,
            totalDiscrepancies,
            processingTime: "2.3m", // TODO: Calculate from actual processing times
          });
        } catch (e) {
          console.error("Failed to load stats:", e);
        }
      }
    };

    loadStats();

    // Refresh stats every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Today's Validations</p>
              <p className="text-2xl font-bold text-foreground mt-1">
                {stats.todayCount}
              </p>
            </div>
            <div className="bg-primary/10 p-3 rounded-lg">
              <FileText className="w-6 h-6 text-primary" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Average Score</p>
              <p className="text-2xl font-bold text-foreground mt-1">
                {stats.avgScore}%
              </p>
            </div>
            <div className="bg-green-500/10 p-3 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-500" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Discrepancies</p>
              <p className="text-2xl font-bold text-foreground mt-1">
                {stats.totalDiscrepancies}
              </p>
            </div>
            <div className="bg-yellow-500/10 p-3 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-yellow-500" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Avg Processing Time</p>
              <p className="text-2xl font-bold text-foreground mt-1">
                {stats.processingTime}
              </p>
            </div>
            <div className="bg-blue-500/10 p-3 rounded-lg">
              <CheckCircle className="w-6 h-6 text-blue-500" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
