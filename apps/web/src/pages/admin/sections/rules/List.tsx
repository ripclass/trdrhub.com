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
import { Archive, CheckCircle2, Clock, FileText, MoreVertical, RefreshCw, Trash2, Upload } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { RulesetRecord, RulesetStatus } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";
import {
  PRIMARY_DOMAIN_OPTIONS,
  RULEBOOK_OPTIONS_BY_DOMAIN,
  ALL_RULEBOOK_OPTIONS,
  RulebookOption,
} from "./constants";

const service = getAdminService();
const PAGE_SIZE = 10;

const FALLBACK_RULESETS: RulesetRecord[] = [];

const STATUS_OPTIONS = [
  { label: "All statuses", value: "all" },
  { label: "Active", value: "active" },
  { label: "Draft", value: "draft" },
  { label: "Archived", value: "archived" },
  { label: "Scheduled", value: "scheduled" },
];

const DOMAIN_FILTER_OPTIONS = [
  { label: "All domains", value: "all" },
  ...PRIMARY_DOMAIN_OPTIONS.map((option) => ({
    label: option.label,
    value: option.value,
  })),
];

const JURISDICTION_OPTIONS = [
  { label: "All jurisdictions", value: "all" },
  // Global & Regional
  { label: "Global", value: "global" },
  { label: "RCEP", value: "rcep" },
  { label: "CPTPP", value: "cptpp" },
  { label: "USMCA", value: "usmca" },
  { label: "ASEAN", value: "asean" },
  { label: "Mercosur", value: "mercosur" },
  { label: "MENA", value: "mena" },
  { label: "Latin America", value: "latam" },
  // Europe
  { label: "EU", value: "eu" },
  { label: "UK", value: "gb" },
  { label: "Germany", value: "de" },
  // Americas
  { label: "US", value: "us" },
  { label: "Canada", value: "ca" },
  { label: "Mexico", value: "mx" },
  { label: "Brazil", value: "br" },
  // Asia-Pacific
  { label: "China", value: "cn" },
  { label: "India", value: "in" },
  { label: "Bangladesh", value: "bd" },
  { label: "Singapore", value: "sg" },
  { label: "Japan", value: "jp" },
  { label: "Korea", value: "kr" },
  { label: "Vietnam", value: "vn" },
  { label: "Thailand", value: "th" },
  { label: "Malaysia", value: "my" },
  { label: "Indonesia", value: "id" },
  { label: "Australia", value: "au" },
  { label: "Hong Kong", value: "hk" },
  { label: "Taiwan", value: "tw" },
  // Middle East
  { label: "UAE", value: "ae" },
  { label: "Saudi Arabia", value: "sa" },
  { label: "Qatar", value: "qa" },
  // Africa
  { label: "South Africa", value: "za" },
  { label: "Nigeria", value: "ng" },
  { label: "Kenya", value: "ke" },
  // Others
  { label: "Turkey", value: "tr" },
  { label: "Pakistan", value: "pk" },
];

const PRIMARY_DOMAIN_LABEL_MAP = new Map(PRIMARY_DOMAIN_OPTIONS.map((option) => [option.value, option.label]));
const RULEBOOK_LOOKUP = new Map<string, RulebookOption>(ALL_RULEBOOK_OPTIONS.map((option) => [option.value, option]));

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
  const [rulebookFilter, setRulebookFilter] = React.useState<string>(searchParams.get("rulesRulebook") ?? "all");

  const [allRulesets, setAllRulesets] = React.useState<RulesetRecord[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [actionRulesetId, setActionRulesetId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [publishDialogOpen, setPublishDialogOpen] = React.useState(false);
  const [rollbackDialogOpen, setRollbackDialogOpen] = React.useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = React.useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [selectedRuleset, setSelectedRuleset] = React.useState<RulesetRecord | null>(null);

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
        page: 1,
        pageSize: 500,
      });
      setAllRulesets(result.items);
      setPage(1);
    } catch (err) {
      console.error("Failed to load rulesets:", err);
      setError("Unable to load rulesets. Retry shortly or check monitoring services.");
      setAllRulesets(FALLBACK_RULESETS);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadRulesets();
  }, [loadRulesets]);

React.useEffect(() => {
  if (rulebookFilter !== "all") {
    const meta = RULEBOOK_LOOKUP.get(rulebookFilter);
    if (meta && domainFilter !== meta.domain) {
      setDomainFilter(meta.domain);
    }
  }
}, [rulebookFilter]);

  const rulebookFilterOptions = React.useMemo(() => {
    const source =
      domainFilter === "all"
        ? ALL_RULEBOOK_OPTIONS
        : RULEBOOK_OPTIONS_BY_DOMAIN[domainFilter] ?? [];

    const options = source.map((option) => {
      const domainLabel = PRIMARY_DOMAIN_LABEL_MAP.get(option.domain) ?? option.domain.toUpperCase();
      const domainLabelShort = domainLabel.split(" (")[0];
      const typeLabel =
        option.type === "base" ? "Base" : option.type === "supplement" ? "Supplement" : "General";

      return {
        label: `${domainLabelShort} · ${option.label}${option.type !== "general" ? ` (${typeLabel})` : ""}`,
        value: option.value,
      };
    });

    return [{ label: "All rulebooks", value: "all" }, ...options];
  }, [domainFilter]);

  const filteredRulesets = React.useMemo(() => {
    let items = [...allRulesets];

    if (statusFilter !== "all") {
      items = items.filter((ruleset) => ruleset.status === statusFilter);
    }

    if (jurisdictionFilter !== "all") {
      items = items.filter((ruleset) => ruleset.jurisdiction === jurisdictionFilter);
    }

    if (rulebookFilter !== "all") {
      items = items.filter((ruleset) => ruleset.domain === rulebookFilter);
    } else if (domainFilter !== "all") {
      const allowed = RULEBOOK_OPTIONS_BY_DOMAIN[domainFilter]?.map((option) => option.value) ?? [];
      items = items.filter((ruleset) => allowed.includes(ruleset.domain) || ruleset.domain === domainFilter);
    }

    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      items = items.filter((ruleset) => {
        const rulebookMeta = RULEBOOK_LOOKUP.get(ruleset.domain);
        const primaryLabel =
          PRIMARY_DOMAIN_LABEL_MAP.get(rulebookMeta?.domain ?? ruleset.domain) ??
          ruleset.domain.toUpperCase();

        return (
          ruleset.rulebookVersion?.toLowerCase().includes(search) ||
          ruleset.rulesetVersion?.toLowerCase().includes(search) ||
          ruleset.domain?.toLowerCase().includes(search) ||
          ruleset.jurisdiction?.toLowerCase().includes(search) ||
          (rulebookMeta?.label.toLowerCase().includes(search) ?? false) ||
          primaryLabel.toLowerCase().includes(search)
        );
      });
    }

    items.sort((a, b) => {
      const aDate = new Date(a.publishedAt ?? a.createdAt ?? 0).getTime();
      const bDate = new Date(b.publishedAt ?? b.createdAt ?? 0).getTime();
      return bDate - aDate;
    });

    return items;
  }, [allRulesets, statusFilter, jurisdictionFilter, rulebookFilter, domainFilter, searchTerm]);

  const totalFiltered = filteredRulesets.length;
  const totalPages = Math.max(1, Math.ceil(totalFiltered / PAGE_SIZE));
  const paginatedRulesets = React.useMemo(
    () => filteredRulesets.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [filteredRulesets, page]
  );

  React.useEffect(() => {
    const maxPages = Math.max(1, Math.ceil(filteredRulesets.length / PAGE_SIZE));
    if (page > maxPages) {
      setPage(maxPages);
    }
  }, [filteredRulesets.length, page]);

  React.useEffect(() => {
    updateQuery({
      rulesPage: page > 1 ? String(page) : null,
      rulesSearch: searchTerm || null,
      rulesStatus: statusFilter !== "all" ? statusFilter : null,
      rulesDomain: domainFilter !== "all" ? domainFilter : null,
      rulesRulebook: rulebookFilter !== "all" ? rulebookFilter : null,
      rulesJurisdiction: jurisdictionFilter !== "all" ? jurisdictionFilter : null,
    });
  }, [page, searchTerm, statusFilter, domainFilter, rulebookFilter, jurisdictionFilter, updateQuery]);

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
    const result = await service.archiveRuleset(ruleset.id);
    setActionRulesetId(null);
    setArchiveDialogOpen(false);
    setSelectedRuleset(null);
    toast({
      title: result.success ? "Ruleset archived" : "Archive failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("archive_ruleset", { entityId: ruleset.id, metadata: { domain: ruleset.domain, jurisdiction: ruleset.jurisdiction } });
      loadRulesets();
    }
  };

  const handleDelete = async (ruleset: RulesetRecord, hard = false) => {
    setActionRulesetId(ruleset.id);
    const result = await service.deleteRuleset(ruleset.id, hard);
    setActionRulesetId(null);
    setDeleteDialogOpen(false);
    setSelectedRuleset(null);
    toast({
      title: result.success ? "Ruleset deleted" : "Delete failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("delete_ruleset", { entityId: ruleset.id, metadata: { domain: ruleset.domain, jurisdiction: ruleset.jurisdiction, hard } });
      loadRulesets();
    }
  };

  const changeDomainFilter = (nextValue: string, resetRulebook = true) => {
    setDomainFilter(nextValue);
    if (resetRulebook) {
      setRulebookFilter("all");
    }
    setPage(1);
  };

  const changeRulebookFilter = (nextValue: string) => {
    setRulebookFilter(nextValue);
    if (nextValue !== "all") {
      const meta = RULEBOOK_LOOKUP.get(nextValue);
      if (meta) {
        setDomainFilter(meta.domain);
      }
    }
    setPage(1);
  };

  const getRulebookDisplay = (domain: string) => {
    const rulebookMeta = RULEBOOK_LOOKUP.get(domain);
    if (!rulebookMeta) {
      const primaryLabel = PRIMARY_DOMAIN_LABEL_MAP.get(domain) ?? domain.toUpperCase();
      return {
        primaryLabel,
        rulebookLabel: domain,
        typeLabel: undefined as string | undefined,
      };
    }

    const primaryLabel =
      PRIMARY_DOMAIN_LABEL_MAP.get(rulebookMeta.domain) ?? rulebookMeta.domain.toUpperCase();
    const typeLabel =
      rulebookMeta.type === "base"
        ? "Base"
        : rulebookMeta.type === "supplement"
        ? "Supplement"
        : undefined;

    return {
      primaryLabel,
      rulebookLabel: rulebookMeta.label,
      typeLabel,
    };
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
          searchPlaceholder="Search by rulebook, version, domain, or jurisdiction"
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
              options: DOMAIN_FILTER_OPTIONS,
              onChange: (value) => {
                changeDomainFilter(String(value || "all"), true);
              },
              allowClear: true,
            },
            {
              label: "Rulebook",
              value: rulebookFilter,
              options: rulebookFilterOptions,
              onChange: (value) => {
                changeRulebookFilter(String(value || "all"));
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
            render: (ruleset: RulesetRecord) => {
              const { primaryLabel, rulebookLabel, typeLabel } = getRulebookDisplay(ruleset.domain);
              return (
                <div className="flex flex-col gap-1">
                  <Badge variant="outline" className="w-fit">
                    {primaryLabel}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {rulebookLabel}
                    {typeLabel ? ` · ${typeLabel}` : ""}
                  </span>
                  <span className="text-xs text-muted-foreground">{ruleset.jurisdiction}</span>
                </div>
              );
            },
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
                      onClick={() => {
                        setSelectedRuleset(ruleset);
                        setArchiveDialogOpen(true);
                      }}
                      disabled={actionRulesetId === ruleset.id}
                    >
                      <Archive className="mr-2 h-4 w-4" /> Archive
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={async () => {
                      const auditLogs = await service.getRulesetAudit(ruleset.id);
                      toast({
                        title: "Audit Log",
                        description: `Found ${auditLogs.length} audit entries for this ruleset.`,
                      });
                    }}
                  >
                    <FileText className="mr-2 h-4 w-4" /> View Audit Log
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => {
                      setSelectedRuleset(ruleset);
                      setDeleteDialogOpen(true);
                    }}
                    disabled={actionRulesetId === ruleset.id}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" /> Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ),
          },
        ]}
        data={paginatedRulesets}
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

      {/* Archive Dialog */}
      <Dialog open={archiveDialogOpen} onOpenChange={setArchiveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Archive Ruleset</DialogTitle>
            <DialogDescription>
              Archiving this ruleset will deactivate all its rules. The ruleset will remain in the system and can be
              restored via rollback.
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
            <Button variant="outline" onClick={() => setArchiveDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => selectedRuleset && handleArchive(selectedRuleset)}
              disabled={!selectedRuleset || actionRulesetId === selectedRuleset.id}
            >
              {actionRulesetId === selectedRuleset?.id ? "Archiving..." : "Archive"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Ruleset</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this ruleset? This will archive the ruleset and deactivate all its rules.
              For permanent deletion, use the "Delete Permanently" option.
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
          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => selectedRuleset && handleDelete(selectedRuleset, true)}
              disabled={!selectedRuleset || actionRulesetId === selectedRuleset.id}
            >
              {actionRulesetId === selectedRuleset?.id ? "Deleting..." : "Delete Permanently"}
            </Button>
            <Button
              onClick={() => selectedRuleset && handleDelete(selectedRuleset, false)}
              disabled={!selectedRuleset || actionRulesetId === selectedRuleset.id}
            >
              {actionRulesetId === selectedRuleset?.id ? "Archiving..." : "Archive Instead"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

