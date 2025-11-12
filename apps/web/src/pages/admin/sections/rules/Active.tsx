import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminEmptyState, AdminFilters, AdminToolbar, DataTable } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { Download, FileText, RefreshCw } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { ActiveRulesetResult, RulesetRecord } from "@/lib/admin/types";

const service = getAdminService();

const DOMAIN_OPTIONS = [
  { label: "All domains", value: "all" },
  { label: "ICC · UCP 600", value: "icc.ucp600" },
  { label: "ICC · eUCP v2.1", value: "icc.eucp2.1" },
  { label: "ICC · ISP98", value: "icc.isp98" },
  { label: "ICC · URDG 758", value: "icc.urdg758" },
  { label: "ICC · URC 522", value: "icc.urc522" },
  { label: "ICC · eURC 1.0", value: "icc.eurc1.0" },
  { label: "ICC · URR 725", value: "icc.urr725" },
  { label: "ICC (Legacy/General)", value: "icc" },
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

interface ActiveRulesetDisplay extends RulesetRecord {
  signedUrl?: string;
}

export function RulesActive() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [domainFilter, setDomainFilter] = React.useState<string>(searchParams.get("activeDomain") ?? "all");
  const [jurisdictionFilter, setJurisdictionFilter] = React.useState<string>(
    searchParams.get("activeJurisdiction") ?? "all"
  );

  const [activeRulesets, setActiveRulesets] = React.useState<ActiveRulesetDisplay[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [downloadingId, setDownloadingId] = React.useState<string | null>(null);

  // Common domain/jurisdiction combinations to check
  const combinations = React.useMemo(() => {
    const allDomains = DOMAIN_OPTIONS.filter((option) => option.value !== "all").map((option) => option.value);
    const domains = domainFilter === "all" ? allDomains : [domainFilter];
    const jurisdictions = jurisdictionFilter === "all" ? ["global", "eu", "us", "bd", "in"] : [jurisdictionFilter];

    return domains.flatMap((domain) => jurisdictions.map((jurisdiction) => ({ domain, jurisdiction })));
  }, [domainFilter, jurisdictionFilter]);

  const loadActiveRulesets = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const results: ActiveRulesetDisplay[] = [];

    try {
      for (const { domain, jurisdiction } of combinations) {
        try {
          const result = await service.getActiveRuleset(domain, jurisdiction, false);
          if (result.ruleset) {
            results.push({
              ...result.ruleset,
              signedUrl: result.signedUrl,
            });
          }
        } catch (err) {
          // Skip if no active ruleset found for this combination
          if (err instanceof Error && err.message.includes("404")) {
            continue;
          }
          console.warn(`Failed to load active ruleset for ${domain}/${jurisdiction}:`, err);
        }
      }
      setActiveRulesets(results);
    } catch (err) {
      console.error("Failed to load active rulesets:", err);
      setError("Unable to load active rulesets. Retry shortly or check monitoring services.");
    } finally {
      setLoading(false);
    }
  }, [combinations]);

  React.useEffect(() => {
    loadActiveRulesets();
  }, [loadActiveRulesets]);

  React.useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (domainFilter !== "all") next.set("activeDomain", domainFilter);
    else next.delete("activeDomain");
    if (jurisdictionFilter !== "all") next.set("activeJurisdiction", jurisdictionFilter);
    else next.delete("activeJurisdiction");
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  }, [domainFilter, jurisdictionFilter, searchParams, setSearchParams]);

  const handleDownload = async (ruleset: ActiveRulesetDisplay) => {
    setDownloadingId(ruleset.id);
    try {
      // Fetch with content to get signed URL or content
      const result = await service.getActiveRuleset(ruleset.domain, ruleset.jurisdiction, true);
      
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
          searchPlaceholder="Filter by domain or jurisdiction"
          filterGroups={[
            {
              label: "Domain",
              value: domainFilter,
              options: DOMAIN_OPTIONS,
              onChange: (value) => {
                setDomainFilter(String(value || "all"));
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
            render: (ruleset: ActiveRulesetDisplay) => (
              <div className="flex flex-col gap-1">
                <Badge variant="outline" className="w-fit">
                  {ruleset.domain.toUpperCase()}
                </Badge>
                <span className="text-xs text-muted-foreground">{ruleset.jurisdiction}</span>
              </div>
            ),
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

