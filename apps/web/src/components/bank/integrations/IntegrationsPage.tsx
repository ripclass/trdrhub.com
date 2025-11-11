/**
 * Bank Integrations Page
 * Manages API tokens and webhook subscriptions for bank integrations
 */
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { APITokensTab } from "@/components/bank/integrations/APITokensTab";
import { WebhooksTab } from "@/components/bank/integrations/WebhooksTab";
import { Key, Webhook } from "lucide-react";

export function IntegrationsPage({ embedded = false }: { embedded?: boolean }) {
  const [activeTab, setActiveTab] = useState("tokens");

  return (
    <div className="space-y-6">
      {!embedded && (
        <div>
          <h2 className="text-2xl font-semibold mb-1">Integrations</h2>
          <p className="text-sm text-muted-foreground">
            Manage API tokens and webhook subscriptions for programmatic access
          </p>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="tokens" className="gap-2">
            <Key className="h-4 w-4" />
            <span>API Tokens</span>
          </TabsTrigger>
          <TabsTrigger value="webhooks" className="gap-2">
            <Webhook className="h-4 w-4" />
            <span>Webhooks</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="tokens" className="mt-6">
          <APITokensTab />
        </TabsContent>

        <TabsContent value="webhooks" className="mt-6">
          <WebhooksTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

