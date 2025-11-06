import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Brain, Plus, Edit } from 'lucide-react';

const mockPrompts = [
  { id: 'prompt-001', name: 'Document Analysis', model: 'GPT-4', version: 'v2.1', usage: '5.2K calls/day', cost: '$245/day' },
  { id: 'prompt-002', name: 'Risk Assessment', model: 'Claude', version: 'v1.5', usage: '2.8K calls/day', cost: '$120/day' },
];

export function LLMPrompts() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">LLM Prompts</h2>
        <p className="text-muted-foreground">
          Manage AI model prompts and templates
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5" />
            Prompt Library
          </CardTitle>
          <CardDescription>Active prompt templates and configurations</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            New Prompt
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockPrompts.map((prompt) => (
              <div key={prompt.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{prompt.name}</p>
                  <p className="text-sm text-muted-foreground">{prompt.model} • Version {prompt.version}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-sm font-semibold text-foreground">{prompt.usage}</p>
                    <p className="text-xs text-muted-foreground">{prompt.cost}</p>
                  </div>
                  <Button variant="outline" size="sm">
                    <Edit className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

