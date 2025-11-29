import * as React from "react";
import { useNavigate } from "react-router-dom";

import { AdminToolbar } from "@/components/admin/ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ArrowLeft, CheckCircle2, FileText, Upload, XCircle } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";
import { PRIMARY_DOMAIN_OPTIONS, RULEBOOK_OPTIONS_BY_DOMAIN } from "./constants";
import type { RulesImportSummary, RulesetRecord } from "@/lib/admin/types";

const service = getAdminService();

const JURISDICTION_OPTIONS = [
  // Global
  { value: "global", label: "Global" },
  
  // FTA/Regional Blocs
  { value: "rcep", label: "RCEP (Asia-Pacific)" },
  { value: "cptpp", label: "CPTPP (Trans-Pacific)" },
  { value: "usmca", label: "USMCA (North America)" },
  { value: "africa", label: "Africa (AfCFTA)" },
  { value: "acfta", label: "ACFTA (ASEAN-China)" },
  { value: "mercosur", label: "Mercosur (South America)" },
  { value: "asean", label: "ASEAN" },
  { value: "eu_gb", label: "EU-UK" },
  { value: "latam", label: "Latin America" },
  { value: "mena", label: "MENA (Middle East/N. Africa)" },
  
  // Europe
  { value: "eu", label: "European Union" },
  { value: "gb", label: "United Kingdom" },
  { value: "de", label: "Germany" },
  { value: "nl", label: "Netherlands" },
  
  // Americas
  { value: "us", label: "United States" },
  { value: "ca", label: "Canada" },
  { value: "mx", label: "Mexico" },
  { value: "br", label: "Brazil" },
  { value: "ar", label: "Argentina" },
  { value: "cl", label: "Chile" },
  { value: "co", label: "Colombia" },
  { value: "pe", label: "Peru" },
  { value: "pa", label: "Panama" },
  
  // Asia-Pacific
  { value: "cn", label: "China" },
  { value: "in", label: "India" },
  { value: "bd", label: "Bangladesh" },
  { value: "sg", label: "Singapore" },
  { value: "jp", label: "Japan" },
  { value: "kr", label: "South Korea" },
  { value: "vn", label: "Vietnam" },
  { value: "th", label: "Thailand" },
  { value: "my", label: "Malaysia" },
  { value: "ph", label: "Philippines" },
  { value: "id", label: "Indonesia" },
  { value: "tw", label: "Taiwan" },
  { value: "hk", label: "Hong Kong" },
  { value: "au", label: "Australia" },
  { value: "nz", label: "New Zealand" },
  { value: "kh", label: "Cambodia" },
  { value: "pk", label: "Pakistan" },
  { value: "lk", label: "Sri Lanka" },
  
  // Middle East
  { value: "ae", label: "UAE" },
  { value: "sa", label: "Saudi Arabia" },
  { value: "eg", label: "Egypt" },
  { value: "qa", label: "Qatar" },
  { value: "kw", label: "Kuwait" },
  { value: "bh", label: "Bahrain" },
  { value: "om", label: "Oman" },
  { value: "jo", label: "Jordan" },
  
  // Africa
  { value: "ma", label: "Morocco" },
  { value: "za", label: "South Africa" },
  { value: "ng", label: "Nigeria" },
  { value: "ke", label: "Kenya" },
  { value: "gh", label: "Ghana" },
  
  // Others
  { value: "tr", label: "Turkey" },
  { value: "kz", label: "Kazakhstan" },
];

export function RulesUpload() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const audit = useAdminAudit("rules-upload");

  const [file, setFile] = React.useState<File | null>(null);
const [domain, setDomain] = React.useState<string>("");
const [rulebook, setRulebook] = React.useState<string>("");
  const [jurisdiction, setJurisdiction] = React.useState<string>("global");
  const [rulesetVersion, setRulesetVersion] = React.useState<string>("1.0.0");
  const [rulebookVersion, setRulebookVersion] = React.useState<string>("");
  const [effectiveFrom, setEffectiveFrom] = React.useState<string>("");
  const [effectiveTo, setEffectiveTo] = React.useState<string>("");
  const [notes, setNotes] = React.useState<string>("");

  const [uploading, setUploading] = React.useState(false);
  const [validationResult, setValidationResult] = React.useState<{
    valid: boolean;
    ruleCount: number;
    errors: string[];
    warnings: string[];
  } | null>(null);
  const [importSummary, setImportSummary] = React.useState<RulesImportSummary | null>(null);
  const [rulesets, setRulesets] = React.useState<RulesetRecord[]>([]);

  // Fetch rulesets on mount
  React.useEffect(() => {
    const fetchRulesets = async () => {
      try {
        const result = await service.listRulesets({ page: 1, pageSize: 1000 });
        setRulesets(result.items);
      } catch (error) {
        console.error("Failed to fetch rulesets:", error);
      }
    };
    fetchRulesets();
  }, []);

  // --------------------------------------------------------
  // AUTO-DETECTION: Extract domain, rulebook_version, ruleset_version
  // Filename format expected:
  //    {domain}-{rulebook_version}-v{ruleset_version}.json
  // Example:
  //    icc.ucp600-UCP600-2007-v1.0.0.json
  //
  // --------------------------------------------------------
  const parseFilename = (filename: string): { domain: string; rulebook_version: string; ruleset_version: string } | null => {
    // remove .json
    const base = filename.replace(/\.json$/i, "");

    // split only first 2 hyphens safely: domain-rulebook-version-vX.Y.Z
    const parts = base.split("-");
    if (parts.length < 3) return null;

    const domain = parts[0];
    const rulebook_version = parts[1];

    // ruleset version always starts with "v"
    const versionPart = parts.slice(2).join("-"); // in case rulebook names have hyphens
    const match = versionPart.match(/^v(\d+\.\d+\.\d+)$/);
    if (!match) return null;

    return {
      domain,
      rulebook_version,
      ruleset_version: match[1],
    };
  };

const rulebookOptionsForDomain = React.useMemo(() => {
  if (!domain) return [];
  return RULEBOOK_OPTIONS_BY_DOMAIN[domain] ?? [];
}, [domain]);

const handleDomainChange = (value: string) => {
  setDomain(value);
  setRulebook("");
};

const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith(".json")) {
        toast({
          title: "Invalid file type",
          description: "Please upload a JSON file.",
          variant: "destructive",
        });
        return;
      }
      
      // ----------------------------------------------
      // AUTO-DETECT when user selects a file
      // ----------------------------------------------
      const detected = parseFilename(selectedFile.name);
      if (detected) {
        setDomain(detected.domain);
        setRulebookVersion(detected.rulebook_version);
        setRulesetVersion(detected.ruleset_version);
        toast({
          title: "Metadata auto-detected",
          description: `Domain: ${detected.domain}, Rulebook: ${detected.rulebook_version}, Version: v${detected.ruleset_version}`,
        });
      } else {
        toast({
          title: "Could not auto-detect metadata",
          description: "Please manually enter domain, rulebook version, and ruleset version.",
          variant: "destructive",
        });
      }
      
      setFile(selectedFile);
      setValidationResult(null);
    }
  };

  const validateFile = async () => {
    if (!file) {
      toast({
        title: "No file selected",
        description: "Please select a JSON file to validate.",
        variant: "destructive",
      });
      return;
    }

    try {
      const text = await file.text();
      const json = JSON.parse(text);

      if (!Array.isArray(json)) {
        setValidationResult({
          valid: false,
          ruleCount: 0,
          errors: ["Ruleset must be an array of rules"],
          warnings: [],
        });
        return;
      }

      // Basic validation
      const errors: string[] = [];
      const warnings: string[] = [];

      if (json.length === 0) {
        warnings.push("Ruleset contains no rules");
      }

      // Check for required fields in each rule
      // Note: domain, jurisdiction, conditions are auto-normalized by backend
      // so we only show warnings for them, not errors
      json.forEach((rule, index) => {
        if (!rule.rule_id) errors.push(`Rule ${index + 1}: Missing rule_id`);
        
        // These fields are auto-fixed by backend - just warn
        if (!rule.domain) {
          warnings.push(`Rule ${index + 1}: Missing domain (will use upload param)`);
        }
        if (!rule.jurisdiction) {
          warnings.push(`Rule ${index + 1}: Missing jurisdiction (will use upload param)`);
        }
        
        // Handle both 'condition' (singular) and 'conditions' (plural)
        const hasConditions = rule.conditions && Array.isArray(rule.conditions);
        const hasCondition = rule.condition && Array.isArray(rule.condition);
        if (!hasConditions && !hasCondition) {
          warnings.push(`Rule ${index + 1}: Missing conditions array (will default to empty)`);
        }
      });

      setValidationResult({
        valid: errors.length === 0,
        ruleCount: json.length,
        errors,
        warnings,
      });

      if (errors.length === 0) {
        toast({
          title: "Validation successful",
          description: `Found ${json.length} rules. Ready to upload.`,
        });
      } else {
        toast({
          title: "Validation failed",
          description: `Found ${errors.length} error(s). Please fix them before uploading.`,
          variant: "destructive",
        });
      }
    } catch (error) {
      setValidationResult({
        valid: false,
        ruleCount: 0,
        errors: [`Invalid JSON: ${error instanceof Error ? error.message : String(error)}`],
        warnings: [],
      });
      toast({
        title: "Invalid JSON",
        description: error instanceof Error ? error.message : "Failed to parse JSON file",
        variant: "destructive",
      });
    }
  };

  const handleUpload = async () => {
    // 1) File presence check
    if (!file) {
      toast({
        title: "No file selected",
        description: "Please select a JSON file.",
        variant: "destructive",
      });
      return;
    }

    // 2) Enforce .json extension
    if (!file.name.toLowerCase().endsWith(".json")) {
      toast({
        title: "Invalid file type",
        description: "Only .json files are allowed.",
        variant: "destructive",
      });
      return;
    }

    if (!domain) {
      toast({
        title: "Domain required",
        description: "Please select a domain.",
        variant: "destructive",
      });
      return;
    }

    if (!rulebookVersion) {
      toast({
        title: "Rulebook version required",
        description: "Please enter the rulebook version (e.g., UCP600:2007).",
        variant: "destructive",
      });
      return;
    }

    if (!rulebook) {
      toast({
        title: "Rulebook required",
        description: "Please select a rulebook.",
        variant: "destructive",
      });
      return;
    }

    // Prevent uploading if a DRAFT already exists with same version
    const alreadyExists = rulesets.some(
      (r) =>
        r.domain === domain &&
        r.rulebook_version === rulebookVersion &&
        r.ruleset_version === rulesetVersion &&
        r.status === "draft"
    );

    if (alreadyExists) {
      toast({
        title: "Draft already exists",
        description: `A DRAFT version ${rulesetVersion} already exists.\nPlease delete or publish it first.`,
        variant: "destructive",
      });
      return;
    }

    // 5) JSON validity pre-check
    const text = await file.text();
    try {
      JSON.parse(text);
    } catch (err) {
      toast({
        title: "Invalid JSON",
        description: "File contains invalid JSON.",
        variant: "destructive",
      });
      return;
    }

    // 6) Optional: lightweight schema check
    try {
      const obj = JSON.parse(text);
      if (!Array.isArray(obj) || obj.length === 0) {
        toast({
          title: "Invalid ruleset file",
          description: "Invalid ruleset file: missing rules[].",
          variant: "destructive",
        });
        return;
      }
    } catch (err) {
      toast({
        title: "Validation failed",
        description: "Ruleset file failed validation.",
        variant: "destructive",
      });
      return;
    }

    if (validationResult && !validationResult.valid) {
      toast({
        title: "Validation required",
        description: "Please validate the file and fix errors before uploading.",
        variant: "destructive",
      });
      return;
    }

    const rulebookOptions = RULEBOOK_OPTIONS_BY_DOMAIN[domain] ?? [];
    const selectedRulebook = rulebookOptions.find((option) => option.value === rulebook);
    if (!selectedRulebook) {
      toast({
        title: "Invalid rulebook selection",
        description: "Selected rulebook is not valid for the chosen domain.",
        variant: "destructive",
      });
      return;
    }

    // 7) Continue to upload

    setUploading(true);
    try {
      const result = await service.uploadRuleset(
        file,
        rulebook,
        jurisdiction,
        rulesetVersion,
        rulebookVersion,
        effectiveFrom || undefined,
        effectiveTo || undefined,
        notes || undefined
      );

        if (result.success && result.data) {
        await audit("upload_ruleset", {
          entityId: result.data.ruleset.id,
          metadata: {
            domain: rulebook,
            jurisdiction,
            ruleCount: result.data.validation.ruleCount,
          },
        });

        toast({
          title: "Ruleset uploaded successfully",
          description: `Uploaded ${result.data.validation.ruleCount} rules. Status: ${result.data.ruleset.status}`,
        });

        // Reset form
        setFile(null);
        setDomain("");
        setJurisdiction("global");
        setRulesetVersion("1.0.0");
        setRulebookVersion("");
        setRulebook("");
        setEffectiveFrom("");
        setEffectiveTo("");
        setNotes("");
        setValidationResult(null);
        setImportSummary(result.data.importSummary ?? null);

        // Navigate back to list
        navigate("/admin?section=rules-list");
      } else {
        toast({
          title: "Upload failed",
          description: result.message || "Failed to upload ruleset",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Upload error",
        description: error instanceof Error ? error.message : "An unexpected error occurred",
        variant: "destructive",
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Upload Ruleset"
        description="Upload a JSON file containing trade rules for LC validation. The file will be validated against the schema before being saved."
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate("/admin?section=rules-list")} className="gap-2">
            <ArrowLeft className="h-4 w-4" /> Back to List
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Upload File</CardTitle>
            <CardDescription>Select a JSON file containing your ruleset</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="file">Ruleset JSON File</Label>
              <Input
                id="file"
                type="file"
                accept=".json"
                onChange={handleFileChange}
                disabled={uploading}
              />
              {file && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <FileText className="h-4 w-4" />
                  <span>{file.name}</span>
                  <span className="text-xs">({(file.size / 1024).toFixed(2)} KB)</span>
                </div>
              )}
            </div>

            <Button onClick={validateFile} disabled={!file || uploading} variant="outline" className="w-full">
              Validate File
            </Button>

            {validationResult && (
              <Alert variant={validationResult.valid ? "default" : "destructive"}>
                {validationResult.valid ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                <AlertTitle>{validationResult.valid ? "Validation Passed" : "Validation Failed"}</AlertTitle>
                <AlertDescription>
                  <div className="space-y-2">
                    <div>
                      <strong>Rules found:</strong> {validationResult.ruleCount}
                    </div>
                    {validationResult.errors.length > 0 && (
                      <div>
                        <strong>Errors:</strong>
                        <ul className="list-disc list-inside mt-1">
                          {validationResult.errors.map((error, i) => (
                            <li key={i} className="text-sm">{error}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {validationResult.warnings.length > 0 && (
                      <div>
                        <strong>Warnings:</strong>
                        <ul className="list-disc list-inside mt-1">
                          {validationResult.warnings.map((warning, i) => (
                            <li key={i} className="text-sm">{warning}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </AlertDescription>
              </Alert>
            )}
            {importSummary && (
              <Alert>
                <AlertTitle>Import Summary</AlertTitle>
                <AlertDescription>
                  <div className="space-y-1 text-sm">
                    <p>
                      Processed {importSummary.totalRules} rules • Inserted {importSummary.inserted} • Updated {importSummary.updated} • Skipped {importSummary.skipped}
                    </p>
                    {importSummary.warnings.length > 0 && (
                      <p>Warnings: {importSummary.warnings.join(", ")}</p>
                    )}
                    {importSummary.errors.length > 0 && (
                      <p className="text-destructive">Errors: {importSummary.errors.join(", ")}</p>
                    )}
                  </div>
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ruleset Metadata</CardTitle>
            <CardDescription>Provide information about this ruleset</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="domain">Domain *</Label>
              <Select value={domain} onValueChange={handleDomainChange} disabled={uploading}>
                <SelectTrigger id="domain">
                  <SelectValue placeholder="Select domain" />
                </SelectTrigger>
                <SelectContent>
                  {PRIMARY_DOMAIN_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="rulebook">Rulebook *</Label>
              <Select
                value={rulebook}
                onValueChange={setRulebook}
                disabled={uploading || !domain}
              >
                <SelectTrigger id="rulebook">
                  <SelectValue placeholder={domain ? "Select rulebook" : "Select domain first"} />
                </SelectTrigger>
                <SelectContent>
                  {rulebookOptionsForDomain.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                      {opt.type === "base"
                        ? " (Base)"
                        : opt.type === "supplement"
                        ? " (Supplement)"
                        : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="jurisdiction">Jurisdiction</Label>
              <Select value={jurisdiction} onValueChange={setJurisdiction} disabled={uploading}>
                <SelectTrigger id="jurisdiction">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {JURISDICTION_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="rulebookVersion">Rulebook Version *</Label>
              <Input
                id="rulebookVersion"
                placeholder="e.g., UCP600:2007"
                value={rulebookVersion}
                onChange={(e) => setRulebookVersion(e.target.value)}
                disabled={uploading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="rulesetVersion">Ruleset Version</Label>
              <Input
                id="rulesetVersion"
                placeholder="e.g., 1.0.0"
                value={rulesetVersion}
                onChange={(e) => setRulesetVersion(e.target.value)}
                disabled={uploading}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="effectiveFrom">Effective From (optional)</Label>
                <Input
                  id="effectiveFrom"
                  type="datetime-local"
                  value={effectiveFrom}
                  onChange={(e) => setEffectiveFrom(e.target.value)}
                  disabled={uploading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="effectiveTo">Effective To (optional)</Label>
                <Input
                  id="effectiveTo"
                  type="datetime-local"
                  value={effectiveTo}
                  onChange={(e) => setEffectiveTo(e.target.value)}
                  disabled={uploading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                placeholder="Additional information about this ruleset..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={uploading}
                rows={3}
              />
            </div>

            <Button
              onClick={handleUpload}
              disabled={uploading || !file || !domain || !rulebook || !rulebookVersion}
              className="w-full"
            >
              {uploading ? (
                <>
                  <Upload className="mr-2 h-4 w-4 animate-spin" /> Uploading...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" /> Upload Ruleset
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

