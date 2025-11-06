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

export default function Budgets() {
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { BarChart3 } from 'lucide-react';

const mockBudgets = [
  { name: 'GPT-4 API', budget: '$10,000', spent: '$7,245', percentage: 72.45, remaining: '$2,755' },
  { name: 'Claude API', budget: '$5,000', spent: '$2,890', percentage: 57.8, remaining: '$2,110' },
  { name: 'Embeddings', budget: '$2,000', spent: '$450', percentage: 22.5, remaining: '$1,550' },
];

export function LLMBudgets() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">LLM Budgets</h2>
        <p className="text-muted-foreground">
          Monitor AI model usage and spending
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {mockBudgets.map((budget) => (
          <Card key={budget.name} className="shadow-soft border-0">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                {budget.name}
              </CardTitle>
              <CardDescription>Monthly budget allocation</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Spent</span>
                  <span className="text-lg font-semibold text-foreground">{budget.spent}</span>
                </div>
                <Progress value={budget.percentage} className="h-3" />
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{budget.percentage.toFixed(1)}% used</span>
                  <span className="text-muted-foreground">{budget.remaining} remaining</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}

