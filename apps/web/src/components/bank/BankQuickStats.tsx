import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { FileText, CheckCircle, AlertTriangle, TrendingUp, CreditCard } from "lucide-react";
import { bankApi } from "@/api/bank";
import { useUsageStats, useInvoices } from "@/hooks/useBilling";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useNavigate } from "react-router-dom";
import { InvoiceStatus } from "@/types/billing";

interface QuickStats {
  todayCount: number;
  avgScore: number;
  totalDiscrepancies: number;
  processingTime: string;
}

export function BankQuickStats() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<QuickStats>({
    todayCount: 0,
    avgScore: 0,
    totalDiscrepancies: 0,
    processingTime: "0m",
  });

  // Fetch billing data
  const { data: usageStats } = useUsageStats();
  const { data: invoicesData } = useInvoices({
    status: [InvoiceStatus.PENDING, InvoiceStatus.OVERDUE],
    limit: 1,
  });

  const hasPendingInvoices = invoicesData?.invoices && invoicesData.invoices.length > 0;
  const quotaPercentage = usageStats
    ? Math.min(100, (usageStats.used / usageStats.limit) * 100)
    : 0;

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
    <div className="space-y-4">
      {/* Billing Signals */}
      {(usageStats || hasPendingInvoices) && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-2">
          {usageStats && (
            <Card className="overflow-hidden">
              <CardContent className="p-6 pt-6">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-muted-foreground mb-2">Usage Quota</p>
                    <div className="space-y-2">
                      <p className="text-2xl font-bold text-foreground tabular-nums">
                        {usageStats.used.toLocaleString()} / {usageStats.limit.toLocaleString()}
                      </p>
                      <Progress value={quotaPercentage} className="h-2" />
                    </div>
                  </div>
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-500/10">
                    <TrendingUp className="h-6 w-6 text-blue-500" />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          {hasPendingInvoices && (
            <Card className="overflow-hidden border-yellow-500/20">
              <CardContent className="p-6 pt-6">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-muted-foreground mb-2">Pending Invoice</p>
                    <div className="flex items-center gap-2">
                      <p className="text-2xl font-bold text-foreground tabular-nums">
                        {invoicesData?.invoices.length || 0}
                      </p>
                      <Badge variant="outline" className="text-yellow-600 border-yellow-600">
                        Action Required
                      </Badge>
                    </div>
                  </div>
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-yellow-500/10">
                    <CreditCard className="h-6 w-6 text-yellow-500" />
                  </div>
                </div>
                <button
                  onClick={() => navigate("/lcopilot/bank-dashboard?tab=billing-invoices")}
                  className="mt-3 text-sm text-primary hover:underline w-full text-left"
                >
                  View invoices →
                </button>
              </CardContent>
            </Card>
          )}
        </div>
      )}
      
      {/* Main Stats */}
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
