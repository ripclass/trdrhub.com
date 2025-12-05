/**
 * Validation Display Component
 * 
 * Shows validation results with errors, warnings, and info
 */

import {
  AlertTriangle,
  XCircle,
  CheckCircle,
  Info,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

interface ValidationIssue {
  code: string;
  severity: "error" | "warning" | "info";
  field: string;
  message: string;
  expected?: string;
  found?: string;
  rule_reference?: string;
}

interface ValidationResult {
  is_valid: boolean;
  status: "passed" | "warnings" | "failed" | "not_validated";
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  info: ValidationIssue[];
}

interface ValidationDisplayProps {
  validation?: ValidationResult | null;
  onValidate?: () => void;
  loading?: boolean;
}

export function ValidationDisplay({
  validation,
  onValidate,
  loading,
}: ValidationDisplayProps) {
  // Not validated yet
  if (!validation) {
    return (
      <Card className="border-dashed">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Info className="h-5 w-5 text-muted-foreground" />
            Validation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Validate your documents against LC requirements and check for consistency.
          </p>
          {onValidate && (
            <Button onClick={onValidate} disabled={loading} variant="outline">
              {loading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Run Validation
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  // Status-based styling
  const statusConfig = {
    passed: {
      icon: CheckCircle,
      color: "text-green-600",
      bgColor: "bg-green-50",
      borderColor: "border-green-200",
      label: "Passed",
    },
    warnings: {
      icon: AlertTriangle,
      color: "text-amber-600",
      bgColor: "bg-amber-50",
      borderColor: "border-amber-200",
      label: "Warnings",
    },
    failed: {
      icon: XCircle,
      color: "text-red-600",
      bgColor: "bg-red-50",
      borderColor: "border-red-200",
      label: "Failed",
    },
    not_validated: {
      icon: Info,
      color: "text-gray-600",
      bgColor: "bg-gray-50",
      borderColor: "border-gray-200",
      label: "Not Validated",
    },
  };

  const config = statusConfig[validation.status] || statusConfig.not_validated;
  const StatusIcon = config.icon;

  const hasIssues = validation.errors.length > 0 || 
                   validation.warnings.length > 0 || 
                   validation.info.length > 0;

  return (
    <Card className={`${config.borderColor} border-2`}>
      <CardHeader className={`${config.bgColor} pb-3`}>
        <div className="flex items-center justify-between">
          <CardTitle className={`text-base flex items-center gap-2 ${config.color}`}>
            <StatusIcon className="h-5 w-5" />
            Validation: {config.label}
          </CardTitle>
          {onValidate && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onValidate}
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>
        <CardDescription className="flex gap-4 mt-1">
          {validation.errors.length > 0 && (
            <span className="text-red-600">
              {validation.errors.length} error{validation.errors.length !== 1 ? "s" : ""}
            </span>
          )}
          {validation.warnings.length > 0 && (
            <span className="text-amber-600">
              {validation.warnings.length} warning{validation.warnings.length !== 1 ? "s" : ""}
            </span>
          )}
          {validation.info.length > 0 && (
            <span className="text-blue-600">
              {validation.info.length} suggestion{validation.info.length !== 1 ? "s" : ""}
            </span>
          )}
          {!hasIssues && (
            <span className="text-green-600">All checks passed</span>
          )}
        </CardDescription>
      </CardHeader>
      
      {hasIssues && (
        <CardContent className="pt-4">
          <Accordion type="multiple" className="space-y-2">
            {/* Errors */}
            {validation.errors.length > 0 && (
              <AccordionItem value="errors" className="border rounded-lg border-red-200">
                <AccordionTrigger className="px-4 hover:no-underline hover:bg-red-50">
                  <div className="flex items-center gap-2">
                    <XCircle className="h-4 w-4 text-red-600" />
                    <span className="font-medium text-red-700">
                      {validation.errors.length} Error{validation.errors.length !== 1 ? "s" : ""}
                    </span>
                    <Badge variant="destructive" className="ml-2">Must Fix</Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4">
                  <div className="space-y-3">
                    {validation.errors.map((error, idx) => (
                      <IssueCard key={idx} issue={error} />
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            )}

            {/* Warnings */}
            {validation.warnings.length > 0 && (
              <AccordionItem value="warnings" className="border rounded-lg border-amber-200">
                <AccordionTrigger className="px-4 hover:no-underline hover:bg-amber-50">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <span className="font-medium text-amber-700">
                      {validation.warnings.length} Warning{validation.warnings.length !== 1 ? "s" : ""}
                    </span>
                    <Badge variant="outline" className="ml-2 border-amber-500 text-amber-700">
                      Review
                    </Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4">
                  <div className="space-y-3">
                    {validation.warnings.map((warning, idx) => (
                      <IssueCard key={idx} issue={warning} />
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            )}

            {/* Info */}
            {validation.info.length > 0 && (
              <AccordionItem value="info" className="border rounded-lg border-blue-200">
                <AccordionTrigger className="px-4 hover:no-underline hover:bg-blue-50">
                  <div className="flex items-center gap-2">
                    <Info className="h-4 w-4 text-blue-600" />
                    <span className="font-medium text-blue-700">
                      {validation.info.length} Suggestion{validation.info.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4">
                  <div className="space-y-3">
                    {validation.info.map((info, idx) => (
                      <IssueCard key={idx} issue={info} />
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            )}
          </Accordion>
        </CardContent>
      )}
    </Card>
  );
}

function IssueCard({ issue }: { issue: ValidationIssue }) {
  const severityColors = {
    error: "border-l-red-500",
    warning: "border-l-amber-500",
    info: "border-l-blue-500",
  };

  return (
    <div className={`border-l-4 ${severityColors[issue.severity]} pl-3 py-2 bg-white rounded-r`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium text-sm">{issue.message}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Field: <code className="bg-muted px-1 rounded">{issue.field}</code>
          </p>
        </div>
        {issue.rule_reference && (
          <Badge variant="outline" className="text-xs flex-shrink-0">
            {issue.rule_reference}
          </Badge>
        )}
      </div>
      
      {(issue.expected || issue.found) && (
        <div className="mt-2 text-xs space-y-1">
          {issue.expected && (
            <div className="flex gap-2">
              <span className="text-muted-foreground w-16">Expected:</span>
              <span className="font-medium text-green-700">{issue.expected}</span>
            </div>
          )}
          {issue.found && (
            <div className="flex gap-2">
              <span className="text-muted-foreground w-16">Found:</span>
              <span className="font-medium text-red-700">{issue.found}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ValidationDisplay;

