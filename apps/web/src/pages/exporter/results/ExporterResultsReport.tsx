import type { ReactNode } from "react";
import { Separator } from "@/components/ui/separator";
import { SectionNav, type SectionNavItem } from "@/components/lcopilot/SectionNav";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface ExporterResultsReportProps {
  /** Whether we're in extraction resolution stage (hides issues + customs) */
  isExtractionResolutionStage: boolean;
  /** Total document count for the section nav badge */
  totalDocuments: number;
  /** Total discrepancy count for the section nav badge */
  totalDiscrepancies: number;

  /** Content for the Required Documents Checklist + Operator Next Actions section */
  checklistContent: ReactNode;
  /** Content for the Issues section (IssuesTab) */
  issuesContent: ReactNode;
  /** Content for the Documents section */
  documentsContent: ReactNode;
  /** Content for the Customs Pack section */
  customsContent: ReactNode;
}

export function ExporterResultsReport({
  isExtractionResolutionStage,
  totalDocuments,
  totalDiscrepancies,
  checklistContent,
  issuesContent,
  documentsContent,
  customsContent,
}: ExporterResultsReportProps) {
  const sections: SectionNavItem[] = [
    { id: "section-checklist", label: "Checklist" },
    {
      id: "section-issues",
      label: "Issues",
      count: totalDiscrepancies,
      hidden: isExtractionResolutionStage,
    },
    { id: "section-documents", label: "Documents", count: totalDocuments },
    {
      id: "section-customs",
      label: "Customs Pack",
      hidden: isExtractionResolutionStage,
    },
  ];

  return (
    <div className="space-y-8">
      <SectionNav sections={sections} />

      {isExtractionResolutionStage && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              Validation Results Unlock After Extraction Resolution
            </CardTitle>
            <CardDescription>
              Review and confirm document fields below. Issues and Customs Pack sections become available once unresolved fields are confirmed.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="border-amber-500/30 text-amber-700 bg-amber-500/5">
                Active: Checklist &amp; Documents
              </Badge>
              <Badge variant="outline" className="border-slate-400/30 text-slate-600">
                Opens later: Issues
              </Badge>
              <Badge variant="outline" className="border-slate-400/30 text-slate-600">
                Opens later: Customs Pack
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Section: Required Documents Checklist + Operator Next Actions */}
      <section id="section-checklist" className="space-y-6 scroll-mt-16">
        {checklistContent}
      </section>

      {/* Section: Issues */}
      {!isExtractionResolutionStage && (
        <>
          <Separator />
          <section id="section-issues" className="space-y-6 scroll-mt-16">
            {issuesContent}
          </section>
        </>
      )}

      {/* Section: Documents */}
      <Separator />
      <section id="section-documents" className="space-y-6 scroll-mt-16">
        {documentsContent}
      </section>

      {/* Section: Customs Pack */}
      {!isExtractionResolutionStage && (
        <>
          <Separator />
          <section id="section-customs" data-testid="section-customs" className="space-y-6 scroll-mt-16">
            {customsContent}
          </section>
        </>
      )}
    </div>
  );
}
