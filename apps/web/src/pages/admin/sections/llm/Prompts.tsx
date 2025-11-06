import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { BrainCircuit, Upload } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services";
import type { PromptRecord } from "@/lib/admin/types";

const service = getAdminService();

export default function Prompts() {
  const enabled = isAdminFeatureEnabled("llm");
  const { toast } = useToast();
  const [prompts, setPrompts] = React.useState<PromptRecord[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!enabled) return;
    service
      .listPrompts()
      .then((data) => setPrompts(data))
      .finally(() => setLoading(false));
  }, [enabled]);

  const publishVersion = async (prompt: PromptRecord) => {
    setActionId(prompt.id);
    const result = await service.publishPromptVersion(prompt.id, {
      diffSummary: "Auto-published from admin console",
    });
    setActionId(null);
    if (result.success && result.data) {
      toast({ title: "Prompt updated", description: `Version ${result.data.latestVersion.version} published.` });
      setPrompts((prev) => prev.map((item) => (item.id === prompt.id ? result.data : item)));
    } else {
      toast({ title: "Publish failed", description: result.message, variant: "destructive" });
    }
  };

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-purple-500/40 bg-purple-500/5 p-6 text-sm text-purple-600">
        Enable the <strong>llm</strong> feature flag to manage prompt templates.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Prompt library"
        description="Prompts powering LC CoPilot flows with embedded version history."
      />

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BrainCircuit className="h-5 w-5 text-primary" />
            Prompt store
          </CardTitle>
          <CardDescription>Latest versions and quick promotion controls</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : prompts.length === 0 ? (
            <AdminEmptyState
              title="No prompts"
              description="Once prompt configs are imported they'll appear here."
            />
          ) : (
            prompts.map((prompt) => (
              <div
                key={prompt.id}
                className="flex flex-col gap-4 rounded-lg border border-border/60 bg-card/60 p-4 md:flex-row md:items-center md:justify-between"
              >
                <div className="space-y-1 text-sm">
                  <p className="font-medium text-foreground">{prompt.name}</p>
                  <p className="text-xs text-muted-foreground">Use case: {prompt.useCase}</p>
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                    <Badge variant="outline">Version {prompt.latestVersion.version}</Badge>
                    <Badge variant="outline">Vars: {prompt.latestVersion.variables.join(", ") || "None"}</Badge>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-xs text-muted-foreground text-right">
                    <p>Updated {new Date(prompt.latestVersion.createdAt).toLocaleString()}</p>
                    <p>By {prompt.latestVersion.createdBy}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => publishVersion(prompt)}
                    disabled={actionId === prompt.id}
                    className="gap-1"
                  >
                    <Upload className="h-4 w-4" /> Promote
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
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

