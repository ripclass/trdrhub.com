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

