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

const service = getAdminService();

const JURISDICTION_OPTIONS = [
  { value: "global", label: "Global" },
  { value: "eu", label: "European Union" },
  { value: "us", label: "United States" },
  { value: "bd", label: "Bangladesh" },
  { value: "in", label: "India" },
  { value: "uk", label: "United Kingdom" },
  { value: "sg", label: "Singapore" },
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
      json.forEach((rule, index) => {
        if (!rule.rule_id) errors.push(`Rule ${index + 1}: Missing rule_id`);
        if (!rule.domain) errors.push(`Rule ${index + 1}: Missing domain`);
        if (!rule.jurisdiction) errors.push(`Rule ${index + 1}: Missing jurisdiction`);
        if (!rule.conditions || !Array.isArray(rule.conditions)) {
          errors.push(`Rule ${index + 1}: Missing or invalid conditions array`);
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
    if (!file) {
      toast({
        title: "No file selected",
        description: "Please select a file to upload.",
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

    if (validationResult && !validationResult.valid) {
      toast({
        title: "Validation required",
        description: "Please validate the file and fix errors before uploading.",
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

