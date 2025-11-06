import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TestTube } from 'lucide-react';

const mockEvals = [
  { id: 'eval-001', name: 'Document Analysis Quality', model: 'GPT-4', score: 94.2, date: '2 days ago', status: 'passed' },
  { id: 'eval-002', name: 'Risk Detection Accuracy', model: 'Claude', score: 91.8, date: '5 days ago', status: 'passed' },
  { id: 'eval-003', name: 'Response Latency', model: 'GPT-3.5', score: 78.5, date: '1 week ago', status: 'review' },
];

export function LLMEvaluations() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">LLM Evaluations</h2>
        <p className="text-muted-foreground">
          Performance and quality metrics for AI models
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TestTube className="w-5 h-5" />
            Evaluation Results
          </CardTitle>
          <CardDescription>Recent model performance evaluations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockEvals.map((eval_) => (
              <div key={eval_.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{eval_.name}</p>
                  <p className="text-sm text-muted-foreground">{eval_.model} • {eval_.date}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-2xl font-bold text-foreground">{eval_.score}</p>
                    <p className="text-xs text-muted-foreground">score</p>
                  </div>
                  <Badge variant={eval_.status === 'passed' ? 'default' : 'secondary'}>
                    {eval_.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

