import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminEmptyState, AdminFilters, AdminToolbar, DataTable } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { Download, FileText, RefreshCw } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { ActiveRulesetResult, RulesetRecord } from "@/lib/admin/types";
import {
  PRIMARY_DOMAIN_OPTIONS,
  RULEBOOK_OPTIONS_BY_DOMAIN,
  ALL_RULEBOOK_OPTIONS,
  RulebookOption,
} from "./constants";

const service = getAdminService();

const DOMAIN_OPTIONS = [
  { label: "All domains", value: "all" },
  ...PRIMARY_DOMAIN_OPTIONS.map((option) => ({
    label: option.label,
    value: option.value,
  })),
];

const JURISDICTION_OPTIONS = [
  { label: "All jurisdictions", value: "all" },
  { label: "Global", value: "global" },
  { label: "EU", value: "eu" },
  { label: "US", value: "us" },
  { label: "Bangladesh", value: "bd" },
  { label: "India", value: "in" },
];

const PRIMARY_DOMAIN_LABEL_MAP = new Map(PRIMARY_DOMAIN_OPTIONS.map((option) => [option.value, option.label]));
const RULEBOOK_LOOKUP = new Map<string, RulebookOption>(ALL_RULEBOOK_OPTIONS.map((option) => [option.value, option]));
const DEFAULT_JURISDICTIONS = ["global", "eu", "us", "bd", "in"];

interface ActiveRulesetDisplay extends RulesetRecord {
  signedUrl?: string;
  rulebookMeta?: RulebookOption;
}

export function RulesActive() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [domainFilter, setDomainFilter] = React.useState<string>(searchParams.get("activeDomain") ?? "all");
  const [rulebookFilter, setRulebookFilter] = React.useState<string>(searchParams.get("activeRulebook") ?? "all");
  const [jurisdictionFilter, setJurisdictionFilter] = React.useState<string>(
    searchParams.get("activeJurisdiction") ?? "all"
  );

  const [activeRulesets, setActiveRulesets] = React.useState<ActiveRulesetDisplay[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [downloadingId, setDownloadingId] = React.useState<string | null>(null);

  const changeDomainFilter = (nextValue: string, resetRulebook = true) => {
    setDomainFilter(nextValue);
    if (resetRulebook) {
      setRulebookFilter("all");
    }
  };

  const changeRulebookFilter = (nextValue: string) => {
    setRulebookFilter(nextValue);
    if (nextValue !== "all") {
      const meta = RULEBOOK_LOOKUP.get(nextValue);
      if (meta) {
        setDomainFilter(meta.domain);
      }
    }
  };

  const getRulebookDisplay = (ruleset: ActiveRulesetDisplay) => {
    const meta = ruleset.rulebookMeta ?? RULEBOOK_LOOKUP.get(ruleset.domain);
    if (!meta) {
      const primaryLabel = PRIMARY_DOMAIN_LABEL_MAP.get(ruleset.domain) ?? ruleset.domain.toUpperCase();
      return {
        primaryLabel,
        rulebookLabel: ruleset.domain,
        typeLabel: undefined as string | undefined,
      };
    }

    const primaryLabel =
      PRIMARY_DOMAIN_LABEL_MAP.get(meta.domain) ?? meta.domain.toUpperCase();
    const typeLabel =
      meta.type === "base" ? "Base" : meta.type === "supplement" ? "Supplement" : undefined;

    return {
      primaryLabel,
      rulebookLabel: meta.label,
      typeLabel,
    };
  };

  const rulebookFilterOptions = React.useMemo(() => {
    const source =
      domainFilter === "all"
        ? ALL_RULEBOOK_OPTIONS
        : RULEBOOK_OPTIONS_BY_DOMAIN[domainFilter] ?? [];

    const options = source.map((option) => {
      const domainLabel = PRIMARY_DOMAIN_LABEL_MAP.get(option.domain) ?? option.domain.toUpperCase();
      const domainLabelShort = domainLabel.split(" (")[0];
      const typeLabel =
        option.type === "base"
          ? "Base"
          : option.type === "supplement"
          ? "Supplement"
          : "General";

      return {
        label: `${domainLabelShort} · ${option.label}${option.type !== "general" ? ` (${typeLabel})` : ""}`,
        value: option.value,
      };
    });

    return [{ label: "All rulebooks", value: "all" }, ...options];
  }, [domainFilter]);

  const loadActiveRulesets = React.useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Use the new bulk endpoint to fetch all active rulesets at once (much faster)
      const allActiveRulesets = await service.getAllActiveRulesets(false);

      // Filter by domain, rulebook, and jurisdiction
      const rulebooksToCheck =
        rulebookFilter !== "all"
          ? ALL_RULEBOOK_OPTIONS.filter((option) => option.value === rulebookFilter)
          : domainFilter === "all"
          ? ALL_RULEBOOK_OPTIONS
          : RULEBOOK_OPTIONS_BY_DOMAIN[domainFilter] ?? [];

      const jurisdictionsToCheck =
        jurisdictionFilter === "all" ? DEFAULT_JURISDICTIONS : [jurisdictionFilter];

      const rulebookValues = new Set(rulebooksToCheck.map((r) => r.value));
      const jurisdictionSet = new Set(jurisdictionsToCheck);

      // Filter and map results
      const filteredResults: ActiveRulesetDisplay[] = allActiveRulesets
        .filter((result) => {
          const ruleset = result.ruleset;
          const matchesDomain =
            domainFilter === "all" ||
            rulebookValues.has(ruleset.domain) ||
            (domainFilter && ruleset.domain.startsWith(domainFilter));
          const matchesRulebook = rulebookFilter === "all" || rulebookValues.has(ruleset.domain);
          const matchesJurisdiction =
            jurisdictionFilter === "all" || jurisdictionSet.has(ruleset.jurisdiction || "global");

          return matchesDomain && matchesRulebook && matchesJurisdiction;
        })
        .map((result) => {
          const ruleset = result.ruleset;
          const rulebookMeta = RULEBOOK_LOOKUP.get(ruleset.domain);
          return {
            ...ruleset,
            signedUrl: result.signedUrl,
            rulebookMeta: rulebookMeta,
          } as ActiveRulesetDisplay;
        });

      // Sort by published date (most recent first)
      filteredResults.sort((a, b) => {
        const aDate = new Date(a.publishedAt ?? a.createdAt ?? 0).getTime();
        const bDate = new Date(b.publishedAt ?? b.createdAt ?? 0).getTime();
        return bDate - aDate;
      });

      setActiveRulesets(filteredResults);
    } catch (err) {
      console.error("Failed to load active rulesets:", err);
      setError("Unable to load active rulesets. Retry shortly or check monitoring services.");
      setActiveRulesets([]);
    } finally {
      setLoading(false);
    }
  }, [domainFilter, rulebookFilter, jurisdictionFilter]);

  React.useEffect(() => {
    loadActiveRulesets();
  }, [loadActiveRulesets]);

  React.useEffect(() => {
    if (rulebookFilter !== "all") {
      const meta = RULEBOOK_LOOKUP.get(rulebookFilter);
      if (meta && domainFilter !== meta.domain) {
        setDomainFilter(meta.domain);
      }
    }
  }, [rulebookFilter]);

  React.useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (domainFilter !== "all") next.set("activeDomain", domainFilter);
    else next.delete("activeDomain");
    if (rulebookFilter !== "all") next.set("activeRulebook", rulebookFilter);
    else next.delete("activeRulebook");
    if (jurisdictionFilter !== "all") next.set("activeJurisdiction", jurisdictionFilter);
    else next.delete("activeJurisdiction");
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  }, [domainFilter, rulebookFilter, jurisdictionFilter, searchParams, setSearchParams]);

  const handleDownload = async (ruleset: ActiveRulesetDisplay) => {
    setDownloadingId(ruleset.id);
    try {
      // Fetch with content to get signed URL or content
      const result = await service.getActiveRuleset(
        ruleset.domain,
        ruleset.jurisdiction ?? "global",
        true
      );
      
      if (result.signedUrl) {
        // Open signed URL in new tab for download
        window.open(result.signedUrl, "_blank");
        toast({
          title: "Download started",
          description: `Downloading ${ruleset.rulebookVersion} ruleset...`,
        });
      } else if (result.content) {
        // Download content as JSON file
        const blob = new Blob([JSON.stringify(result.content, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${ruleset.domain}-${ruleset.jurisdiction}-${ruleset.rulesetVersion}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast({
          title: "Download complete",
          description: `${ruleset.rulebookVersion} ruleset downloaded.`,
        });
      } else {
        throw new Error("No download URL or content available");
      }
    } catch (err) {
      console.error("Download failed:", err);
      toast({
        title: "Download failed",
        description: err instanceof Error ? err.message : "Unable to download ruleset.",
        variant: "destructive",
      });
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Active Rulesets"
        description="View and download currently active rulesets used for LC validation."
        actions={
          <Button variant="outline" size="sm" onClick={loadActiveRulesets} disabled={loading} className="gap-2">
            <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
          </Button>
        }
      >
        <AdminFilters
          searchPlaceholder="Filter by domain, rulebook, or jurisdiction"
          filterGroups={[
            {
              label: "Domain",
              value: domainFilter,
              options: DOMAIN_OPTIONS,
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
            render: (ruleset: ActiveRulesetDisplay) => (
              <div className="flex flex-col gap-1">
                <span className="font-medium">{ruleset.rulebookVersion}</span>
                <span className="text-xs text-muted-foreground">v{ruleset.rulesetVersion}</span>
              </div>
            ),
          },
          {
            key: "domain",
            header: "Domain",
            render: (ruleset: ActiveRulesetDisplay) => {
              const { primaryLabel, rulebookLabel, typeLabel } = getRulebookDisplay(ruleset);
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
            key: "ruleCount",
            header: "Rules",
            render: (ruleset: ActiveRulesetDisplay) => (
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span>{ruleset.ruleCount}</span>
              </div>
            ),
          },
          {
            key: "publishedAt",
            header: "Published",
            render: (ruleset: ActiveRulesetDisplay) => (
              <div className="flex flex-col gap-1">
                {ruleset.publishedAt ? (
                  <>
                    <span className="text-sm">{new Date(ruleset.publishedAt).toLocaleDateString()}</span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(ruleset.publishedAt).toLocaleTimeString()}
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
            render: (ruleset: ActiveRulesetDisplay) => (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDownload(ruleset)}
                disabled={downloadingId === ruleset.id}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                {downloadingId === ruleset.id ? "Downloading..." : "Download JSON"}
              </Button>
            ),
          },
        ]}
        data={activeRulesets}
        loading={loading}
        emptyState={
          <AdminEmptyState
            icon={<FileText className="h-8 w-8" />}
            title="No active rulesets found"
            description={
              domainFilter !== "all" || jurisdictionFilter !== "all"
                ? "No active rulesets match the selected filters. Try adjusting your filters or upload a new ruleset."
                : "No active rulesets are currently published. Upload and publish a ruleset to get started."
            }
          />
        }
      />
    </div>
  );
}

