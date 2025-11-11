/**
 * API Tokens Tab Component
 * Manages API tokens for bank integrations
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
import { useToast } from "@/hooks/use-toast";
import { bankTokensApi, APIToken, APITokenCreate } from "@/api/bank";
import { Key, Plus, Copy, Trash2, Eye, EyeOff, Calendar, Clock, Activity } from "lucide-react";
import { format } from "date-fns";

export function APITokensTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showTokenDialog, setShowTokenDialog] = useState(false);
  const [newToken, setNewToken] = useState<string | null>(null);
  const [revokeTokenId, setRevokeTokenId] = useState<string | null>(null);

  // Fetch tokens
  const { data: tokensData, isLoading } = useQuery({
    queryKey: ["bank-tokens"],
    queryFn: () => bankTokensApi.list(false),
  });

  // Create token mutation
  const createMutation = useMutation({
    mutationFn: (data: APITokenCreate) => bankTokensApi.create(data),
    onSuccess: (response) => {
      setNewToken(response.token);
      setShowCreateDialog(false);
      setShowTokenDialog(true);
      queryClient.invalidateQueries({ queryKey: ["bank-tokens"] });
      toast({
        title: "Token created",
        description: "Your API token has been created. Store it securely.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to create token",
        description: error?.message || "An error occurred",
        variant: "destructive",
      });
    },
  });

  // Revoke token mutation
  const revokeMutation = useMutation({
    mutationFn: ({ tokenId, reason }: { tokenId: string; reason?: string }) =>
      bankTokensApi.revoke(tokenId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-tokens"] });
      setRevokeTokenId(null);
      toast({
        title: "Token revoked",
        description: "The API token has been revoked successfully.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to revoke token",
        description: error?.message || "An error occurred",
        variant: "destructive",
      });
    },
  });

  const handleCopyToken = (token: string) => {
    navigator.clipboard.writeText(token);
    toast({
      title: "Copied",
      description: "Token copied to clipboard",
    });
  };

  const tokens = tokensData?.tokens || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">API Tokens</h3>
          <p className="text-sm text-muted-foreground">
            Create and manage API tokens for programmatic access to LCopilot
          </p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Token
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Create API Token</DialogTitle>
              <DialogDescription>
                Create a new API token for programmatic access. You'll only see the token once.
              </DialogDescription>
            </DialogHeader>
            <CreateTokenForm
              onSubmit={(data) => createMutation.mutate(data)}
              isLoading={createMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Token Display Dialog (shown once after creation) */}
      <Dialog open={showTokenDialog} onOpenChange={setShowTokenDialog}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Token Created</DialogTitle>
            <DialogDescription>
              Store this token securely. You won't be able to see it again.
            </DialogDescription>
          </DialogHeader>
          {newToken && (
            <div className="space-y-4">
              <div className="relative">
                <Input
                  value={newToken}
                  readOnly
                  className="font-mono text-sm pr-10"
                />
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full"
                  onClick={() => handleCopyToken(newToken)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
              <div className="rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-4">
                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                  ⚠️ This is the only time you'll see this token. Make sure to copy it now.
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setShowTokenDialog(false)}>I've Saved It</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Tokens List */}
      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Loading tokens...</div>
      ) : tokens.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <Key className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No API tokens</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Create your first API token to get started with programmatic access
              </p>
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Token
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {tokens.map((token) => (
            <TokenCard
              key={token.id}
              token={token}
              onRevoke={() => setRevokeTokenId(token.id)}
            />
          ))}
        </div>
      )}

      {/* Revoke Confirmation Dialog */}
      <AlertDialog open={!!revokeTokenId} onOpenChange={(open) => !open && setRevokeTokenId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke API Token?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The token will immediately stop working.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => revokeTokenId && revokeMutation.mutate({ tokenId: revokeTokenId })}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Revoke Token
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function CreateTokenForm({
  onSubmit,
  isLoading,
}: {
  onSubmit: (data: APITokenCreate) => void;
  isLoading: boolean;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [scopes, setScopes] = useState<string[]>([]);
  const [expiresAt, setExpiresAt] = useState("");

  const availableScopes = [
    { id: "read:results", label: "Read Results" },
    { id: "write:results", label: "Write Results" },
    { id: "read:jobs", label: "Read Jobs" },
    { id: "write:jobs", label: "Write Jobs" },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name,
      description: description || undefined,
      scopes,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
    });
  };

  const toggleScope = (scopeId: string) => {
    setScopes((prev) =>
      prev.includes(scopeId) ? prev.filter((s) => s !== scopeId) : [...prev, scopeId]
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Token Name *</Label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Production API"
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
        <Label>Scopes *</Label>
        <div className="grid grid-cols-2 gap-2">
          {availableScopes.map((scope) => (
            <Button
              key={scope.id}
              type="button"
              variant={scopes.includes(scope.id) ? "default" : "outline"}
              onClick={() => toggleScope(scope.id)}
              className="justify-start"
            >
              {scopes.includes(scope.id) && <Eye className="h-4 w-4 mr-2" />}
              {scope.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="expires_at">Expires At (Optional)</Label>
        <Input
          id="expires_at"
          type="datetime-local"
          value={expiresAt}
          onChange={(e) => setExpiresAt(e.target.value)}
        />
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isLoading || !name || scopes.length === 0}>
          {isLoading ? "Creating..." : "Create Token"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function TokenCard({ token, onRevoke }: { token: APIToken; onRevoke: () => void }) {
  const [showDetails, setShowDetails] = useState(false);

  const isExpired = token.expires_at && new Date(token.expires_at) < new Date();
  const isRevoked = !!token.revoked_at;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base">{token.name}</CardTitle>
            {token.description && (
              <CardDescription>{token.description}</CardDescription>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isRevoked ? (
              <Badge variant="destructive">Revoked</Badge>
            ) : isExpired ? (
              <Badge variant="secondary">Expired</Badge>
            ) : token.is_active ? (
              <Badge variant="default">Active</Badge>
            ) : (
              <Badge variant="secondary">Inactive</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Key className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-xs">{token.token_prefix}****...****</span>
            </div>
            {token.last_used_at && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="h-4 w-4" />
                <span>Last used {format(new Date(token.last_used_at), "MMM d, yyyy")}</span>
              </div>
            )}
            {token.usage_count > 0 && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Activity className="h-4 w-4" />
                <span>{token.usage_count} uses</span>
              </div>
            )}
          </div>

          {showDetails && (
            <div className="space-y-2 text-sm border-t pt-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-muted-foreground">Scopes</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {token.scopes.map((scope) => (
                      <Badge key={scope} variant="outline" className="text-xs">
                        {scope}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-muted-foreground">Created</p>
                  <p className="mt-1">
                    {format(new Date(token.created_at), "MMM d, yyyy")}
                  </p>
                </div>
                {token.expires_at && (
                  <div>
                    <p className="text-muted-foreground">Expires</p>
                    <p className="mt-1">
                      {format(new Date(token.expires_at), "MMM d, yyyy")}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowDetails(!showDetails)}
            >
              {showDetails ? (
                <>
                  <EyeOff className="h-4 w-4 mr-2" />
                  Hide Details
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4 mr-2" />
                  Show Details
                </>
              )}
            </Button>
            {!isRevoked && (
              <Button variant="destructive" size="sm" onClick={onRevoke}>
                <Trash2 className="h-4 w-4 mr-2" />
                Revoke
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

