/**
 * Webhooks Tab Component
 * Manages webhook subscriptions and delivery logs
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  bankWebhooksApi,
  WebhookSubscription,
  WebhookSubscriptionCreate,
  WebhookDelivery,
} from "@/api/bank";
import {
  Webhook,
  Plus,
  Trash2,
  TestTube,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  ExternalLink,
} from "lucide-react";
import { format } from "date-fns";

export function WebhooksTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showSecretDialog, setShowSecretDialog] = useState(false);
  const [newSecret, setNewSecret] = useState<string | null>(null);
  const [deleteSubscriptionId, setDeleteSubscriptionId] = useState<string | null>(null);
  const [selectedSubscription, setSelectedSubscription] = useState<string | null>(null);

  // Fetch subscriptions
  const { data: subscriptionsData, isLoading } = useQuery({
    queryKey: ["bank-webhooks"],
    queryFn: () => bankWebhooksApi.list(),
  });

  // Create subscription mutation
  const createMutation = useMutation({
    mutationFn: (data: WebhookSubscriptionCreate) => bankWebhooksApi.create(data),
    onSuccess: (response) => {
      setNewSecret(response.secret);
      setShowCreateDialog(false);
      setShowSecretDialog(true);
      queryClient.invalidateQueries({ queryKey: ["bank-webhooks"] });
      toast({
        title: "Webhook created",
        description: "Your webhook subscription has been created.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to create webhook",
        description: error?.message || "An error occurred",
        variant: "destructive",
      });
    },
  });

  // Delete subscription mutation
  const deleteMutation = useMutation({
    mutationFn: (subscriptionId: string) => bankWebhooksApi.delete(subscriptionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-webhooks"] });
      setDeleteSubscriptionId(null);
      toast({
        title: "Webhook deleted",
        description: "The webhook subscription has been deleted.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to delete webhook",
        description: error?.message || "An error occurred",
        variant: "destructive",
      });
    },
  });

  // Test webhook mutation
  const testMutation = useMutation({
    mutationFn: (subscriptionId: string) => bankWebhooksApi.test(subscriptionId),
    onSuccess: (response) => {
      toast({
        title: "Webhook tested",
        description: `Status: ${response.status} (${response.http_status_code || "N/A"})`,
      });
      queryClient.invalidateQueries({ queryKey: ["bank-webhooks"] });
    },
    onError: (error: any) => {
      toast({
        title: "Test failed",
        description: error?.message || "An error occurred",
        variant: "destructive",
      });
    },
  });

  const subscriptions = subscriptionsData?.subscriptions || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Webhook Subscriptions</h3>
          <p className="text-sm text-muted-foreground">
            Configure webhooks to receive real-time notifications about LC validation events
          </p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Webhook
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>Create Webhook Subscription</DialogTitle>
              <DialogDescription>
                Configure a webhook endpoint to receive LC validation events
              </DialogDescription>
            </DialogHeader>
            <CreateWebhookForm
              onSubmit={(data) => createMutation.mutate(data)}
              isLoading={createMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Secret Display Dialog */}
      <Dialog open={showSecretDialog} onOpenChange={setShowSecretDialog}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Webhook Secret</DialogTitle>
            <DialogDescription>
              Store this secret securely. You'll need it to verify webhook signatures.
            </DialogDescription>
          </DialogHeader>
          {newSecret && (
            <div className="space-y-4">
              <div className="relative">
                <Input value={newSecret} readOnly className="font-mono text-sm pr-10" />
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full"
                  onClick={() => {
                    navigator.clipboard.writeText(newSecret);
                    toast({ title: "Copied", description: "Secret copied to clipboard" });
                  }}
                >
                  Copy
                </Button>
              </div>
              <div className="rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-4">
                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                  ⚠️ This is the only time you'll see this secret. Make sure to copy it now.
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setShowSecretDialog(false)}>I've Saved It</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Subscriptions List */}
      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Loading webhooks...</div>
      ) : subscriptions.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <Webhook className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No webhook subscriptions</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Create your first webhook subscription to receive real-time events
              </p>
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Webhook
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {subscriptions.map((subscription) => (
            <WebhookCard
              key={subscription.id}
              subscription={subscription}
              onDelete={() => setDeleteSubscriptionId(subscription.id)}
              onTest={() => testMutation.mutate(subscription.id)}
              onViewDeliveries={() => setSelectedSubscription(subscription.id)}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={!!deleteSubscriptionId}
        onOpenChange={(open) => !open && setDeleteSubscriptionId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Webhook Subscription?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The webhook will stop receiving events immediately.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                deleteSubscriptionId && deleteMutation.mutate(deleteSubscriptionId)
              }
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Deliveries Dialog */}
      {selectedSubscription && (
        <WebhookDeliveriesDialog
          subscriptionId={selectedSubscription}
          onClose={() => setSelectedSubscription(null)}
        />
      )}
    </div>
  );
}

function CreateWebhookForm({
  onSubmit,
  isLoading,
}: {
  onSubmit: (data: WebhookSubscriptionCreate) => void;
  isLoading: boolean;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState<string[]>([]);
  const [timeoutSeconds, setTimeoutSeconds] = useState(30);
  const [retryCount, setRetryCount] = useState(3);

  const availableEvents = [
    { id: "validation.completed", label: "Validation Completed" },
    { id: "validation.failed", label: "Validation Failed" },
    { id: "discrepancy.created", label: "Discrepancy Created" },
    { id: "approval.required", label: "Approval Required" },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name,
      description: description || undefined,
      url,
      events,
      timeout_seconds: timeoutSeconds,
      retry_count: retryCount,
    });
  };

  const toggleEvent = (eventId: string) => {
    setEvents((prev) =>
      prev.includes(eventId) ? prev.filter((e) => e !== eventId) : [...prev, eventId]
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Webhook Name *</Label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Production Webhook"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional description"
          rows={2}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="url">Webhook URL *</Label>
        <Input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/webhook"
          required
        />
      </div>

      <div className="space-y-2">
        <Label>Events *</Label>
        <div className="grid grid-cols-2 gap-2">
          {availableEvents.map((event) => (
            <Button
              key={event.id}
              type="button"
              variant={events.includes(event.id) ? "default" : "outline"}
              onClick={() => toggleEvent(event.id)}
              className="justify-start"
            >
              {event.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="timeout">Timeout (seconds)</Label>
          <Input
            id="timeout"
            type="number"
            min="1"
            max="300"
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(parseInt(e.target.value) || 30)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="retries">Retry Count</Label>
          <Input
            id="retries"
            type="number"
            min="0"
            max="10"
            value={retryCount}
            onChange={(e) => setRetryCount(parseInt(e.target.value) || 3)}
          />
        </div>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isLoading || !name || !url || events.length === 0}>
          {isLoading ? "Creating..." : "Create Webhook"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function WebhookCard({
  subscription,
  onDelete,
  onTest,
  onViewDeliveries,
}: {
  subscription: WebhookSubscription;
  onDelete: () => void;
  onTest: () => void;
  onViewDeliveries: () => void;
}) {
  const successRate =
    subscription.success_count + subscription.failure_count > 0
      ? Math.round(
          (subscription.success_count /
            (subscription.success_count + subscription.failure_count)) *
            100
        )
      : 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base">{subscription.name}</CardTitle>
            {subscription.description && (
              <CardDescription>{subscription.description}</CardDescription>
            )}
            <div className="flex items-center gap-2 mt-2">
              <Badge variant={subscription.is_active ? "default" : "secondary"}>
                {subscription.is_active ? "Active" : "Inactive"}
              </Badge>
              {subscription.last_delivery_at && (
                <span className="text-xs text-muted-foreground">
                  Last delivery: {format(new Date(subscription.last_delivery_at), "MMM d, yyyy HH:mm")}
                </span>
              )}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2 text-sm">
            <div>
              <p className="text-muted-foreground">URL</p>
              <p className="font-mono text-xs break-all">{subscription.url}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Events</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {subscription.events.map((event) => (
                  <Badge key={event} variant="outline" className="text-xs">
                    {event}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-muted-foreground">Success Rate</p>
                <p className="font-semibold">{successRate}%</p>
              </div>
              <div>
                <p className="text-muted-foreground">Success</p>
                <p className="font-semibold text-green-600">{subscription.success_count}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Failures</p>
                <p className="font-semibold text-red-600">{subscription.failure_count}</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onTest}>
              <TestTube className="h-4 w-4 mr-2" />
              Test
            </Button>
            <Button variant="outline" size="sm" onClick={onViewDeliveries}>
              <ExternalLink className="h-4 w-4 mr-2" />
              View Deliveries
            </Button>
            <Button variant="destructive" size="sm" onClick={onDelete} className="ml-auto">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function WebhookDeliveriesDialog({
  subscriptionId,
  onClose,
}: {
  subscriptionId: string;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  // Fetch deliveries
  const { data: deliveriesData, isLoading } = useQuery({
    queryKey: ["bank-webhook-deliveries", subscriptionId, statusFilter],
    queryFn: () =>
      bankWebhooksApi.listDeliveries(subscriptionId, {
        status: statusFilter,
        limit: 50,
      }),
  });

  // Replay mutation
  const replayMutation = useMutation({
    mutationFn: (deliveryId: string) => bankWebhooksApi.replay(deliveryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-webhook-deliveries", subscriptionId] });
      toast({
        title: "Delivery replayed",
        description: "The webhook delivery has been replayed.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to replay",
        description: error?.message || "An error occurred",
        variant: "destructive",
      });
    },
  });

  const deliveries = deliveriesData?.deliveries || [];

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[900px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Webhook Deliveries</DialogTitle>
          <DialogDescription>View delivery history and replay failed deliveries</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Label>Filter by status:</Label>
            <select
              value={statusFilter || ""}
              onChange={(e) => setStatusFilter(e.target.value || undefined)}
              className="px-3 py-1 border rounded-md"
            >
              <option value="">All</option>
              <option value="success">Success</option>
              <option value="failed">Failed</option>
              <option value="pending">Pending</option>
              <option value="retrying">Retrying</option>
            </select>
          </div>

          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading deliveries...</div>
          ) : deliveries.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No deliveries found</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Attempt</TableHead>
                  <TableHead>HTTP Status</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {deliveries.map((delivery) => (
                  <TableRow key={delivery.id}>
                    <TableCell className="font-medium">{delivery.event_type}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          delivery.status === "success"
                            ? "default"
                            : delivery.status === "failed"
                            ? "destructive"
                            : "secondary"
                        }
                      >
                        {delivery.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {delivery.attempt_number} / {delivery.max_attempts}
                    </TableCell>
                    <TableCell>
                      {delivery.http_status_code ? (
                        <span
                          className={
                            delivery.http_status_code >= 200 && delivery.http_status_code < 300
                              ? "text-green-600"
                              : "text-red-600"
                          }
                        >
                          {delivery.http_status_code}
                        </span>
                      ) : (
                        "-"
                      )}
                    </TableCell>
                    <TableCell>
                      {delivery.duration_ms ? `${delivery.duration_ms}ms` : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {format(new Date(delivery.started_at), "MMM d, HH:mm:ss")}
                    </TableCell>
                    <TableCell>
                      {delivery.status === "failed" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => replayMutation.mutate(delivery.id)}
                          disabled={replayMutation.isPending}
                        >
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        <DialogFooter>
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

