import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { Banknote } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services";
import type { LLMBudget } from "@/lib/admin/types";

const service = getAdminService();

export function LLMBudgets() {
  const enabled = isAdminFeatureEnabled("llm");
  const { toast } = useToast();
  const [budgets, setBudgets] = React.useState<LLMBudget[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!enabled) return;
    service
      .listLLMBudgets()
      .then((data) => setBudgets(data))
      .finally(() => setLoading(false));
  }, [enabled]);

  const adjustLimit = async (budget: LLMBudget) => {
    const input = window.prompt("Set new monthly limit", String(budget.monthlyLimit));
    if (!input) return;
    const limit = Number(input);
    if (Number.isNaN(limit)) {
      toast({ title: "Invalid number", variant: "destructive" });
      return;
    }
    setActionId(budget.id);
    const result = await service.updateLLMBudget(budget.id, { monthlyLimit: limit });
    setActionId(null);
    if (result.success) {
      toast({ title: "Budget updated" });
      setBudgets((prev) => prev.map((item) => (item.id === budget.id ? { ...item, monthlyLimit: limit } : item)));
    } else {
      toast({ title: "Update failed", description: result.message, variant: "destructive" });
    }
  };

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-purple-500/40 bg-purple-500/5 p-6 text-sm text-purple-600">
        Toggle the <strong>llm</strong> flag to monitor model budgets and spending forecasts.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="LLM budgets"
        description="Track monthly spend caps for OpenAI, Anthropic and internal evaluators."
      />

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Card key={index} className="border-border/60">
              <CardHeader>
                <Skeleton className="h-5 w-32" />
              </CardHeader>
              <CardContent className="space-y-3">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-8 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : budgets.length === 0 ? (
        <AdminEmptyState
          title="No budgets configured"
          description="Set cost guardrails to avoid runaway usage."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {budgets.map((budget) => {
            const percentage = Math.min(100, Math.round((budget.spendingToDate / budget.monthlyLimit) * 100));
            return (
              <Card key={budget.id} className="border-border/60">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between text-base">
                    <span>{budget.service}</span>
                    <Badge variant="outline">{budget.provider}</Badge>
                  </CardTitle>
                  <CardDescription>Monthly cap {budget.currency} {(budget.monthlyLimit).toLocaleString()}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Spent to date</span>
                    <span className="font-semibold text-foreground">{budget.currency} {budget.spendingToDate.toLocaleString()}</span>
                  </div>
                  <Progress value={percentage} className="h-2" />
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{percentage}% used</span>
                    <span>Forecast {budget.currency} {budget.forecast.toLocaleString()}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Hard limit: {budget.currency} {budget.hardLimit.toLocaleString()}
                  </div>
                  <div className="flex flex-wrap gap-2 text-[10px] text-muted-foreground">
                    {budget.emails.map((email) => (
                      <Badge key={email} variant="outline">
                        {email}
                      </Badge>
                    ))}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full gap-1"
                    onClick={() => adjustLimit(budget)}
                    disabled={actionId === budget.id}
                  >
                    <Banknote className="h-4 w-4" /> Adjust limit
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default LLMBudgets;
