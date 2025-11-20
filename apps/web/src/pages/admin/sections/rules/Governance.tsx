import * as React from "react";
import { useToast } from "@/components/ui/use-toast";
import { getAdminService } from "@/lib/admin/services";
import type { RuleRecord } from "@/lib/admin/types";
import { PRIMARY_DOMAIN_OPTIONS } from "./constants";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Loader2, RefreshCw, Settings2 } from "lucide-react";

const DOCUMENT_TYPE_OPTIONS = [
  { label: "All documents", value: "all" },
  { label: "Letter of Credit", value: "lc" },
  { label: "Commercial Invoice", value: "invoice" },
  { label: "Bill of Lading", value: "bol" },
  { label: "Guarantee", value: "guarantee" },
];

const SEVERITY_OPTIONS = [
  { label: "All severities", value: "all" },
  { label: "Info", value: "info" },
  { label: "Warning", value: "warning" },
  { label: "Fail", value: "fail" },
  { label: "Risk", value: "risk" },
];

const STATUS_OPTIONS = [
  { label: "Active", value: "active" },
  { label: "Inactive", value: "inactive" },
  { label: "All", value: "all" },
];

export function RulesGovernance() {
  const service = getAdminService();
  const { toast } = useToast();
  const [rules, setRules] = React.useState<RuleRecord[]>([]);
  const [page, setPage] = React.useState(1);
  const [pageSize] = React.useState(25);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [search, setSearch] = React.useState("");
  const [selectedRule, setSelectedRule] = React.useState<RuleRecord | null>(null);
  const [jsonDraft, setJsonDraft] = React.useState("");
  const [jsonError, setJsonError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [filters, setFilters] = React.useState({
    domain: "all",
    documentType: "all",
    severity: "all",
    status: "active",
  });

  const loadRules = React.useCallback(async () => {
    setLoading(true);
    try {
      const response = await service.listRules({
        page,
        pageSize,
        domain: filters.domain !== "all" ? filters.domain : undefined,
        documentType: filters.documentType !== "all" ? filters.documentType : undefined,
        severity: filters.severity !== "all" ? filters.severity : undefined,
        isActive:
          filters.status === "all" ? undefined : filters.status === "active",
        search: search || undefined,
      });
      setRules(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error(error);
      toast({
        title: "Unable to load rules",
        description: error instanceof Error ? error.message : "Unexpected error",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [service, filters, page, pageSize, search, toast]);

  React.useEffect(() => {
    loadRules();
  }, [loadRules]);

  const openRule = (rule: RuleRecord) => {
    setSelectedRule(rule);
    setJsonDraft(JSON.stringify(rule, null, 2));
    setJsonError(null);
  };

  const closeDialog = () => {
    setSelectedRule(null);
    setJsonDraft("");
    setJsonError(null);
  };

  const handleToggleActive = async (rule: RuleRecord, nextValue: boolean) => {
    try {
      const updated = await service.updateRule(rule.ruleId, { isActive: nextValue });
      setRules((current) =>
        current.map((item) => (item.ruleId === rule.ruleId ? updated : item)),
      );
      if (selectedRule?.ruleId === rule.ruleId) {
        setSelectedRule(updated);
      }
      toast({
        title: nextValue ? "Rule activated" : "Rule archived",
      });
    } catch (error) {
      console.error(error);
      toast({
        title: "Failed to update rule",
        description: error instanceof Error ? error.message : "Unexpected error",
        variant: "destructive",
      });
    }
  };

  const handleSeverityChange = async (rule: RuleRecord, severity: string) => {
    try {
      const updated = await service.updateRule(rule.ruleId, { severity });
      setRules((current) =>
        current.map((item) => (item.ruleId === rule.ruleId ? updated : item)),
      );
      if (selectedRule?.ruleId === rule.ruleId) {
        setSelectedRule(updated);
      }
    } catch (error) {
      toast({
        title: "Failed to update severity",
        description: error instanceof Error ? error.message : "Unexpected error",
        variant: "destructive",
      });
    }
  };

  const handleJsonSave = async () => {
    if (!selectedRule) return;
    try {
      setSaving(true);
      const parsed = JSON.parse(jsonDraft);
      const updated = await service.updateRule(selectedRule.ruleId, { ruleJson: parsed });
      setRules((current) =>
        current.map((item) => (item.ruleId === updated.ruleId ? updated : item)),
      );
      setSelectedRule(updated);
      toast({ title: "Rule updated" });
    } catch (error) {
      console.error(error);
      setJsonError(
        error instanceof Error
          ? error.message
          : "Failed to parse JSON payload",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleBulkSync = async () => {
    try {
      await service.bulkSyncRules();
      toast({
        title: "Bulk sync triggered",
        description: "Active rulesets are being refreshed.",
      });
      loadRules();
    } catch (error) {
      toast({
        title: "Bulk sync failed",
        description: error instanceof Error ? error.message : "Unexpected error",
        variant: "destructive",
      });
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <div>
          <h1 className="text-3xl font-bold">Rules Governance</h1>
          <p className="text-muted-foreground">
            Inspect, edit, and sync individual trade rules without touching the core ruleset JSON.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Input
            placeholder="Search by rule ID, title, or description"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            className="max-w-sm"
          />
          <Select
            value={filters.domain}
            onValueChange={(value) => {
              setFilters((prev) => ({ ...prev, domain: value }));
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Domain" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All domains</SelectItem>
              {PRIMARY_DOMAIN_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={filters.documentType}
            onValueChange={(value) => {
              setFilters((prev) => ({ ...prev, documentType: value }));
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Document type" />
            </SelectTrigger>
            <SelectContent>
              {DOCUMENT_TYPE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={filters.severity}
            onValueChange={(value) => {
              setFilters((prev) => ({ ...prev, severity: value }));
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              {SEVERITY_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={filters.status}
            onValueChange={(value) => {
              setFilters((prev) => ({ ...prev, status: value }));
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={loadRules} disabled={loading} className="gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Refresh
          </Button>
          <Button variant="secondary" onClick={handleBulkSync} className="gap-2">
            <Settings2 className="h-4 w-4" />
            Bulk Sync Active Rules
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Rules</CardTitle>
            <CardDescription>
              {total.toLocaleString()} rules found • Page {page} of {totalPages}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={page === 1 || loading}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={page === totalPages || loading}
            >
              Next
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Rule</TableHead>
                <TableHead>Domain</TableHead>
                <TableHead>Document</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Requires LLM</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-10">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : rules.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-10 text-muted-foreground">
                    No rules match your filters.
                  </TableCell>
                </TableRow>
              ) : (
                rules.map((rule) => (
                  <TableRow key={rule.ruleId} className="cursor-pointer hover:bg-muted/40" onClick={() => openRule(rule)}>
                    <TableCell className="space-y-1">
                      <div className="font-medium">{rule.ruleId}</div>
                      <div className="text-sm text-muted-foreground">{rule.title}</div>
                    </TableCell>
                    <TableCell>{rule.domain.toUpperCase()}</TableCell>
                    <TableCell className="capitalize">{rule.documentType}</TableCell>
                    <TableCell>
                      <Badge variant={rule.severity === "fail" ? "destructive" : "secondary"}>
                        {rule.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>{rule.requiresLlm ? "Yes" : "No"}</TableCell>
                    <TableCell>
                      <Badge variant={rule.isActive ? "default" : "outline"}>
                        {rule.isActive ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(rule.updatedAt).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={!!selectedRule} onOpenChange={(open) => (!open ? closeDialog() : null)}>
        <DialogContent className="max-w-3xl">
          {selectedRule && (
            <>
              <DialogHeader>
                <DialogTitle>{selectedRule.ruleId}</DialogTitle>
                <DialogDescription>{selectedRule.title}</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Active</p>
                    <p className="text-xs text-muted-foreground">
                      Toggle availability in the governance table.
                    </p>
                  </div>
                  <Switch
                    checked={selectedRule.isActive}
                    onCheckedChange={(value) => handleToggleActive(selectedRule, value)}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Severity</p>
                  </div>
                  <Select
                    value={selectedRule.severity}
                    onValueChange={(value) => handleSeverityChange(selectedRule, value)}
                  >
                    <SelectTrigger className="w-[160px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {["info", "warning", "fail", "risk"].map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">Rule JSON</p>
                      <p className="text-xs text-muted-foreground">
                        Edit the raw rule payload (must be valid JSON).
                      </p>
                    </div>
                  </div>
                  <Textarea
                    value={jsonDraft}
                    onChange={(event) => {
                      setJsonDraft(event.target.value);
                      setJsonError(null);
                    }}
                    className="font-mono text-sm min-h-[240px]"
                  />
                  {jsonError && (
                    <p className="text-sm text-destructive">
                      {jsonError}
                    </p>
                  )}
                </div>
              </div>
              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={closeDialog}>
                  Cancel
                </Button>
                <Button onClick={handleJsonSave} disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Save Changes
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

