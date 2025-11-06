import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminEmptyState, AdminToolbar, DataTable } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { Copy, KeyRound, RefreshCw, ShieldOff, Sparkles } from "lucide-react";

import { getAdminService } from "@/lib/admin/services/index";
import type { ApiKeyRecord } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const PAGE_SIZE = 10;
const DEFAULT_SCOPES = ["read", "write", "ingest", "webhooks"];

export function SecurityAccess() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const audit = useAdminAudit("security-access");
  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("keysPage") ?? "1")));
  const [environment, setEnvironment] = React.useState<string>(searchParams.get("keysEnv") ?? "all");

  const [apiKeys, setApiKeys] = React.useState<ApiKeyRecord[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);

  const [createOpen, setCreateOpen] = React.useState(false);
  const [newName, setNewName] = React.useState("");
  const [newEnv, setNewEnv] = React.useState<ApiKeyRecord["environment"]>("production");
  const [selectedScopes, setSelectedScopes] = React.useState<string[]>(["read"]);
  const [generatedToken, setGeneratedToken] = React.useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const updateQuery = React.useCallback(
    (updates: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([key, value]) => {
        if (!value) next.delete(key);
        else next.set(key, value);
      });
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const loadKeys = React.useCallback(() => {
    setLoading(true);
    service
      .listApiKeys({
        page,
        pageSize: PAGE_SIZE,
        environment: environment === "all" ? undefined : environment,
      })
      .then((result) => {
        setApiKeys(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [page, environment]);

  React.useEffect(() => {
    updateQuery({
      keysPage: page === 1 ? null : String(page),
      keysEnv: environment === "all" ? null : environment,
    });
    loadKeys();
  }, [page, environment, loadKeys, updateQuery]);

  const handleCreate = async () => {
    if (!newName.trim()) {
      toast({ title: "Name required", variant: "destructive" });
      return;
    }
    setActionId("create");
    const result = await service.createApiKey({
      name: newName.trim(),
      environment: newEnv,
      scopes: selectedScopes,
    });
    setActionId(null);
    if (result.success && result.data) {
      setGeneratedToken(result.data.token);
      toast({ title: "API key generated" });
      setNewName("");
      setSelectedScopes(["read"]);
      loadKeys();
      await audit("create_api_key", { metadata: { name: newName.trim(), environment: newEnv, scopes: selectedScopes } });
    } else {
      toast({ title: "Generation failed", description: result.message, variant: "destructive" });
    }
  };

  const handleRotate = async (id: string) => {
    setActionId(id);
    const result = await service.rotateApiKey(id);
    setActionId(null);
    if (result.success && result.data) {
      setGeneratedToken(result.data.token);
      toast({ title: "API key rotated", description: "Copy the new token immediately." });
      loadKeys();
      await audit("rotate_api_key", { entityId: id });
    } else {
      toast({ title: "Rotation failed", description: result.message, variant: "destructive" });
    }
  };

  const handleRevoke = async (id: string) => {
    setActionId(id);
    const result = await service.revokeApiKey(id);
    setActionId(null);
    toast({
      title: result.success ? "API key revoked" : "Revoke failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("revoke_api_key", { entityId: id });
      loadKeys();
    }
  };

  const copyToken = async (token: string | undefined) => {
    if (!token) return;
    await navigator.clipboard.writeText(token);
    toast({ title: "Copied to clipboard" });
  };

  const scopesToggle = (scope: string) => {
    setSelectedScopes((prev) =>
      prev.includes(scope) ? prev.filter((item) => item !== scope) : [...prev, scope],
    );
  };

  const environments = [
    { label: "All environments", value: "all" },
    { label: "Production", value: "production" },
    { label: "Staging", value: "staging" },
    { label: "Development", value: "development" },
  ];

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="API credential management"
        description="Issue, rotate and revoke tokens that integrate with LCopilot."
        actions={
          <Dialog open={createOpen} onOpenChange={(open) => { setCreateOpen(open); setGeneratedToken(null); }}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-2">
                <Sparkles className="h-4 w-4" /> Generate key
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Create new API key</DialogTitle>
                <DialogDescription>Token is shown once. Store it securely after generation.</DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">Name</label>
                  <Input value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="Partner integration" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">Environment</label>
                  <Select value={newEnv} onValueChange={(value) => setNewEnv(value as ApiKeyRecord["environment"])}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="production">Production</SelectItem>
                      <SelectItem value="staging">Staging</SelectItem>
                      <SelectItem value="development">Development</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">Scopes</label>
                  <div className="flex flex-wrap gap-2">
                    {DEFAULT_SCOPES.map((scope) => (
                      <Button
                        key={scope}
                        type="button"
                        variant={selectedScopes.includes(scope) ? "default" : "outline"}
                        size="sm"
                        onClick={() => scopesToggle(scope)}
                      >
                        {scope}
                      </Button>
                    ))}
                  </div>
                </div>
                {generatedToken && (
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-muted-foreground">New token</label>
                    <div className="flex items-center gap-2">
                      <Input value={generatedToken} readOnly />
                      <Button type="button" variant="outline" size="icon" onClick={() => copyToken(generatedToken)}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button onClick={handleCreate} disabled={actionId === "create"}>
                  Generate key
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <Select value={environment} onValueChange={(value) => { setEnvironment(value); setPage(1); }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {environments.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={loadKeys} disabled={loading} className="gap-2">
          <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
        </Button>
      </div>

      <DataTable
        columns={[
          {
            key: "name",
            header: "Key",
            render: (key) => (
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">{key.name}</p>
                <p className="text-xs font-mono text-muted-foreground">{key.hashedKey ?? "Stored securely"}</p>
              </div>
            ),
          },
          {
            key: "environment",
            header: "Environment",
            render: (key) => <Badge variant="outline">{key.environment}</Badge>,
          },
          {
            key: "scopes",
            header: "Scopes",
            render: (key) => (
              <div className="flex flex-wrap gap-1">
                {key.scopes.map((scope) => (
                  <Badge key={scope} variant="secondary" className="text-[10px]">
                    {scope}
                  </Badge>
                ))}
              </div>
            ),
          },
          {
            key: "createdAt",
            header: "Issued",
            render: (key) => (
              <span className="text-xs text-muted-foreground">
                {key.createdAt ? new Date(key.createdAt).toLocaleString() : "—"}
              </span>
            ),
          },
          {
            key: "lastUsedAt",
            header: "Last used",
            render: (key) => (
              <span className="text-xs text-muted-foreground">
                {key.lastUsedAt ? new Date(key.lastUsedAt).toLocaleString() : "Never"}
              </span>
            ),
          },
          {
            key: "status",
            header: "Status",
            render: (key) => (
              <Badge variant={key.status === "active" ? "default" : key.status === "rotating" ? "secondary" : "outline"}>
                {key.status}
              </Badge>
            ),
          },
          {
            key: "actions",
            header: "Actions",
            align: "right",
            render: (key) => (
              <div className="flex items-center justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRotate(key.id)}
                  disabled={actionId === key.id}
                  className="gap-1"
                >
                  <KeyRound className="h-4 w-4" /> Rotate
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1 text-rose-600"
                  onClick={() => handleRevoke(key.id)}
                  disabled={actionId === key.id}
                >
                  <ShieldOff className="h-4 w-4" /> Revoke
                </Button>
              </div>
            ),
          },
        ]}
        data={apiKeys}
        loading={loading}
        emptyState={<AdminEmptyState title="No API keys" description="Generate a key to integrate external systems." />}
        footer={
          total > PAGE_SIZE && (
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    className={page === 1 ? "pointer-events-none opacity-50" : undefined}
                    onClick={(event) => {
                      event.preventDefault();
                      if (page > 1) setPage(page - 1);
                    }}
                  />
                </PaginationItem>
                <PaginationItem>
                  <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
                </PaginationItem>
                <PaginationItem>
                  <PaginationNext
                    href="#"
                    className={page >= totalPages ? "pointer-events-none opacity-50" : undefined}
                    onClick={(event) => {
                      event.preventDefault();
                      if (page < totalPages) setPage(page + 1);
                    }}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          )
        }
      />

      {loading && apiKeys.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      )}
    </div>
  );
}

export default SecurityAccess;
