import * as React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { AdminEmptyState, AdminFilters, AdminToolbar, DataTable } from "@/components/admin/ui";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { useToast } from "@/components/ui/use-toast";
import { Archive, CheckCircle2, Clock, FileText, MoreVertical, RefreshCw, Upload } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { RulesetRecord, RulesetStatus } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const PAGE_SIZE = 10;

const FALLBACK_RULESETS: RulesetRecord[] = [
  {
    id: "ruleset-fallback-1",
    domain: "icc",
    jurisdiction: "global",
    rulesetVersion: "1.0.0",
    rulebookVersion: "UCP600:2007",
    filePath: "rules/icc/fallback.json",
    status: "active",
    checksumMd5: "fallback-checksum",
    ruleCount: 39,
    createdAt: new Date().toISOString(),
    publishedAt: new Date().toISOString(),
    publishedBy: "system",
  },
];

const STATUS_OPTIONS = [
  { label: "All statuses", value: "all" },
  { label: "Active", value: "active" },
  { label: "Draft", value: "draft" },
  { label: "Archived", value: "archived" },
  { label: "Scheduled", value: "scheduled" },
];

const DOMAIN_OPTIONS = [
  { label: "All domains", value: "all" },
  { label: "ICC", value: "icc" },
  { label: "Regulations", value: "regulations" },
  { label: "Incoterms", value: "incoterms" },
  { label: "VAT", value: "vat" },
  { label: "Sanctions", value: "sanctions" },
  { label: "AML", value: "aml" },
  { label: "Customs", value: "customs" },
  { label: "Shipping", value: "shipping" },
];

const JURISDICTION_OPTIONS = [
  { label: "All jurisdictions", value: "all" },
  { label: "Global", value: "global" },
  { label: "EU", value: "eu" },
  { label: "US", value: "us" },
  { label: "Bangladesh", value: "bd" },
  { label: "India", value: "in" },
];

function formatRelativeTime(iso: string | undefined): string {
  if (!iso) return "Never";
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  const diffMonths = Math.floor(diffDays / 30);
  return `${diffMonths}mo ago`;
}

function getStatusBadge(status: RulesetStatus) {
  switch (status) {
    case "active":
      return <Badge variant="default" className="bg-green-500/10 text-green-700 dark:text-green-400">Active</Badge>;
    case "draft":
      return <Badge variant="secondary">Draft</Badge>;
    case "archived":
      return <Badge variant="outline">Archived</Badge>;
    case "scheduled":
      return <Badge variant="outline" className="bg-blue-500/10 text-blue-700 dark:text-blue-400">Scheduled</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export function RulesList() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const audit = useAdminAudit("rules-list");

  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("rulesPage") ?? "1")));
  const [searchTerm, setSearchTerm] = React.useState(searchParams.get("rulesSearch") ?? "");
  const [statusFilter, setStatusFilter] = React.useState<string>(searchParams.get("rulesStatus") ?? "all");
  const [domainFilter, setDomainFilter] = React.useState<string>(searchParams.get("rulesDomain") ?? "all");
  const [jurisdictionFilter, setJurisdictionFilter] = React.useState<string>(
    searchParams.get("rulesJurisdiction") ?? "all"
  );

  const [rulesets, setRulesets] = React.useState<RulesetRecord[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [actionRulesetId, setActionRulesetId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [publishDialogOpen, setPublishDialogOpen] = React.useState(false);
  const [rollbackDialogOpen, setRollbackDialogOpen] = React.useState(false);
  const [selectedRuleset, setSelectedRuleset] = React.useState<RulesetRecord | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const updateQuery = React.useCallback(
    (updates: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([key, value]) => {
        if (value === null || value === "") next.delete(key);
        else next.set(key, value);
      });
      if (next.toString() !== searchParams.toString()) {
        setSearchParams(next, { replace: true });
      }
    },
    [searchParams, setSearchParams]
  );

  const loadRulesets = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await service.listRulesets({
        page,
        pageSize: PAGE_SIZE,
        domain: domainFilter !== "all" ? domainFilter : undefined,
        jurisdiction: jurisdictionFilter !== "all" ? jurisdictionFilter : undefined,
        status: statusFilter !== "all" ? (statusFilter as RulesetStatus) : undefined,
      });
      setRulesets(result.items);
      setTotal(result.total);
    } catch (err) {
      console.error("Failed to load rulesets:", err);
      setError("Unable to load rulesets. Retry shortly or check monitoring services.");
      setRulesets(FALLBACK_RULESETS);
      setTotal(FALLBACK_RULESETS.length);
    } finally {
      setLoading(false);
    }
  }, [page, domainFilter, jurisdictionFilter, statusFilter]);

  React.useEffect(() => {
    loadRulesets();
  }, [loadRulesets]);

  React.useEffect(() => {
    updateQuery({
      rulesPage: page > 1 ? String(page) : null,
      rulesSearch: searchTerm || null,
      rulesStatus: statusFilter !== "all" ? statusFilter : null,
      rulesDomain: domainFilter !== "all" ? domainFilter : null,
      rulesJurisdiction: jurisdictionFilter !== "all" ? jurisdictionFilter : null,
    });
  }, [page, searchTerm, statusFilter, domainFilter, jurisdictionFilter, updateQuery]);

  const handlePublish = async (ruleset: RulesetRecord) => {
    setActionRulesetId(ruleset.id);
    const result = await service.publishRuleset(ruleset.id);
    setActionRulesetId(null);
    setPublishDialogOpen(false);
    setSelectedRuleset(null);
    toast({
      title: result.success ? "Ruleset published" : "Publish failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("publish_ruleset", { entityId: ruleset.id, metadata: { domain: ruleset.domain, jurisdiction: ruleset.jurisdiction } });
      loadRulesets();
    }
  };

  const handleRollback = async (ruleset: RulesetRecord) => {
    setActionRulesetId(ruleset.id);
    const result = await service.rollbackRuleset(ruleset.id);
    setActionRulesetId(null);
    setRollbackDialogOpen(false);
    setSelectedRuleset(null);
    toast({
      title: result.success ? "Ruleset rolled back" : "Rollback failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("rollback_ruleset", { entityId: ruleset.id, metadata: { domain: ruleset.domain, jurisdiction: ruleset.jurisdiction } });
      loadRulesets();
    }
  };

  const handleArchive = async (ruleset: RulesetRecord) => {
    setActionRulesetId(ruleset.id);
    // Note: Archive functionality would need to be added to the service
    setActionRulesetId(null);
    toast({
      title: "Archive not implemented",
      description: "Archive functionality will be available soon.",
      variant: "default",
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Rules Management"
        description="Upload, validate, and publish trade rules (ICC, regulations, etc.) for LC validation."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadRulesets} disabled={loading} className="gap-2">
              <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
            </Button>
            <Button size="sm" onClick={() => navigate("/admin?section=rules-upload")} className="gap-2">
              <Upload className="h-4 w-4" /> Upload Ruleset
            </Button>
          </div>
        }
      >
        <AdminFilters
          searchPlaceholder="Search by rulebook version, domain, or jurisdiction"
          searchValue={searchTerm}
          onSearchChange={(value) => {
            setSearchTerm(value);
            setPage(1);
          }}
          filterGroups={[
            {
              label: "Status",
              value: statusFilter,
              options: STATUS_OPTIONS,
              onChange: (value) => {
                setStatusFilter(String(value || "all"));
                setPage(1);
              },
              allowClear: true,
            },
            {
              label: "Domain",
              value: domainFilter,
              options: DOMAIN_OPTIONS,
              onChange: (value) => {
                setDomainFilter(String(value || "all"));
                setPage(1);
              },
              allowClear: true,
            },
            {
              label: "Jurisdiction",
              value: jurisdictionFilter,
              options: JURISDICTION_OPTIONS,
              onChange: (value) => {
                setJurisdictionFilter(String(value || "all"));
                setPage(1);
              },
              allowClear: true,
            },
          ]}
        />
      </AdminToolbar>

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
          {error}
        </div>
      )}

      <DataTable
        columns={[
          {
            key: "rulebookVersion",
            header: "Rulebook",
            render: (ruleset: RulesetRecord) => (
              <div className="flex flex-col gap-1">
                <span className="font-medium">{ruleset.rulebookVersion}</span>
                <span className="text-xs text-muted-foreground">v{ruleset.rulesetVersion}</span>
              </div>
            ),
          },
          {
            key: "domain",
            header: "Domain",
            render: (ruleset: RulesetRecord) => (
              <div className="flex flex-col gap-1">
                <Badge variant="outline" className="w-fit">
                  {ruleset.domain.toUpperCase()}
                </Badge>
                <span className="text-xs text-muted-foreground">{ruleset.jurisdiction}</span>
              </div>
            ),
          },
          {
            key: "status",
            header: "Status",
            render: (ruleset: RulesetRecord) => getStatusBadge(ruleset.status),
          },
          {
            key: "ruleCount",
            header: "Rules",
            render: (ruleset: RulesetRecord) => (
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span>{ruleset.ruleCount}</span>
              </div>
            ),
          },
          {
            key: "publishedAt",
            header: "Published",
            render: (ruleset: RulesetRecord) => (
              <div className="flex flex-col gap-1">
                {ruleset.publishedAt ? (
                  <>
                    <span className="text-sm">{formatRelativeTime(ruleset.publishedAt)}</span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(ruleset.publishedAt).toLocaleDateString()}
                    </span>
                  </>
                ) : (
                  <span className="text-sm text-muted-foreground">Not published</span>
                )}
              </div>
            ),
          },
          {
            key: "actions",
            header: "",
            render: (ruleset: RulesetRecord) => (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {ruleset.status === "draft" && (
                    <DropdownMenuItem
                      onClick={() => {
                        setSelectedRuleset(ruleset);
                        setPublishDialogOpen(true);
                      }}
                      disabled={actionRulesetId === ruleset.id}
                    >
                      <CheckCircle2 className="mr-2 h-4 w-4" /> Publish
                    </DropdownMenuItem>
                  )}
                  {ruleset.status === "archived" && (
                    <DropdownMenuItem
                      onClick={() => {
                        setSelectedRuleset(ruleset);
                        setRollbackDialogOpen(true);
                      }}
                      disabled={actionRulesetId === ruleset.id}
                    >
                      <Clock className="mr-2 h-4 w-4" /> Rollback
                    </DropdownMenuItem>
                  )}
                  {ruleset.status !== "archived" && (
                    <DropdownMenuItem
                      onClick={() => handleArchive(ruleset)}
                      disabled={actionRulesetId === ruleset.id}
                    >
                      <Archive className="mr-2 h-4 w-4" /> Archive
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={async () => {
                      // TODO: Navigate to audit log view when implemented
                      const auditLogs = await service.getRulesetAudit(ruleset.id);
                      toast({
                        title: "Audit Log",
                        description: `Found ${auditLogs.length} audit entries for this ruleset.`,
                      });
                    }}
                  >
                    <FileText className="mr-2 h-4 w-4" /> View Audit Log
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ),
          },
        ]}
        data={rulesets}
        loading={loading}
        emptyState={
          <AdminEmptyState
            icon={<FileText className="h-8 w-8" />}
            title="No rulesets found"
            description="Upload your first ruleset to get started with LC validation rules."
            action={
              <Button size="sm" onClick={() => navigate("/admin?section=rules-upload")}>
                <Upload className="mr-2 h-4 w-4" /> Upload Ruleset
              </Button>
            }
          />
        }
      />

      {totalPages > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  if (page > 1) setPage(page - 1);
                }}
                className={page === 1 ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
            <PaginationItem>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
            </PaginationItem>
            <PaginationItem>
              <PaginationNext
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  if (page < totalPages) setPage(page + 1);
                }}
                className={page === totalPages ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}

      {/* Publish Dialog */}
      <Dialog open={publishDialogOpen} onOpenChange={setPublishDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Publish Ruleset</DialogTitle>
            <DialogDescription>
              Publishing this ruleset will make it active and archive any currently active ruleset for the same domain
              and jurisdiction. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {selectedRuleset && (
            <div className="space-y-2">
              <div>
                <span className="text-sm font-medium">Rulebook:</span> {selectedRuleset.rulebookVersion}
              </div>
              <div>
                <span className="text-sm font-medium">Domain:</span> {selectedRuleset.domain}
              </div>
              <div>
                <span className="text-sm font-medium">Jurisdiction:</span> {selectedRuleset.jurisdiction}
              </div>
              <div>
                <span className="text-sm font-medium">Rules:</span> {selectedRuleset.ruleCount}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPublishDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => selectedRuleset && handlePublish(selectedRuleset)}
              disabled={!selectedRuleset || actionRulesetId === selectedRuleset.id}
            >
              {actionRulesetId === selectedRuleset?.id ? "Publishing..." : "Publish"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rollback Dialog */}
      <Dialog open={rollbackDialogOpen} onOpenChange={setRollbackDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rollback Ruleset</DialogTitle>
            <DialogDescription>
              Rolling back will make this ruleset active again and archive the currently active ruleset for the same
              domain and jurisdiction. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {selectedRuleset && (
            <div className="space-y-2">
              <div>
                <span className="text-sm font-medium">Rulebook:</span> {selectedRuleset.rulebookVersion}
              </div>
              <div>
                <span className="text-sm font-medium">Domain:</span> {selectedRuleset.domain}
              </div>
              <div>
                <span className="text-sm font-medium">Jurisdiction:</span> {selectedRuleset.jurisdiction}
              </div>
              <div>
                <span className="text-sm font-medium">Rules:</span> {selectedRuleset.ruleCount}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRollbackDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => selectedRuleset && handleRollback(selectedRuleset)}
              disabled={!selectedRuleset || actionRulesetId === selectedRuleset.id}
            >
              {actionRulesetId === selectedRuleset?.id ? "Rolling back..." : "Rollback"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

