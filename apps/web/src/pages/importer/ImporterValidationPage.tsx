/**
 * Importer-side validation surface.
 *
 * Serves both Moment 1 (Draft LC Risk Analysis) and Moment 2 (Supplier
 * Document Review) via a `moment` prop. Upload → extract-review → validate
 * runs against the same /api/validate endpoint as the exporter page, just
 * with `workflowTypeEnum` flipped so ValidationSession.workflow_type gets
 * persisted as importer_draft_lc or importer_supplier_docs.
 *
 * Intentionally simpler than ExportLCUpload. The exporter page has a
 * two-step flow (LC intake, then supporting docs) driven by the backend's
 * intake-only branch. The importer flows don't need that split — drop
 * everything, kick off extract-only, review, validate.
 */

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import { FileText, Upload, X } from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  ImporterSidebar,
  type ImporterSidebarSection,
} from "@/components/importer/ImporterSidebar";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  useValidate,
  type ExtractionReadyResponse,
  parseExtractionResponse,
} from "@/hooks/use-lcopilot";
import { useExtractionPayloadStore } from "@/hooks/use-extraction-payload-store";
import { ExtractionReview } from "@/components/lcopilot/ExtractionReview";
import { PreparationGuide } from "@/components/lcopilot/PreparationGuide";

import { IMPORTER_MOMENTS, type ImporterMoment } from "./importerMoments";

export interface ImporterValidationPageProps {
  moment: ImporterMoment;
}

export function ImporterValidationPage({ moment }: ImporterValidationPageProps) {
  const config = IMPORTER_MOMENTS[moment];
  const { toast } = useToast();
  const navigate = useNavigate();
  const { validate, isLoading: isValidating } = useValidate();
  const [extractionPayload, setExtractionPayload] =
    useExtractionPayloadStore<ExtractionReadyResponse>();
  const [files, setFiles] = useState<File[]>([]);

  const onDrop = useCallback((accepted: File[]) => {
    setFiles((prev) => [...prev, ...accepted]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const onStart = async () => {
    if (files.length === 0) {
      toast({ title: "No files selected", variant: "destructive" });
      return;
    }
    try {
      const response = await validate({
        files,
        extractOnly: true,
        workflowTypeEnum: config.workflowType,
      });
      const parsed = parseExtractionResponse(response);
      if (parsed) {
        setExtractionPayload(parsed);
      } else {
        toast({
          title: "Unexpected response shape",
          description: "Review the console for details.",
          variant: "destructive",
        });
      }
    } catch (err: any) {
      toast({
        title: "Extraction failed",
        description: err?.message || "Unknown error",
        variant: "destructive",
      });
    }
  };

  const onBackToUpload = () => {
    setExtractionPayload(null);
    setFiles([]);
  };

  const onStartValidation = ({ jobId }: { jobId: string }) => {
    // Leave the payload in sessionStorage so the results page can rehydrate.
    navigate(`/lcopilot/results-v2/${jobId}`);
  };

  const jobId = extractionPayload?.jobId || extractionPayload?.job_id;

  const sidebarSection: ImporterSidebarSection =
    moment === "draft_lc" ? "draft-lc" : "supplier-docs";

  const handleSectionChange = useCallback(
    (next: ImporterSidebarSection) => {
      if (next === "dashboard") {
        navigate("/lcopilot/importer-dashboard");
      } else if (next === "draft-lc") {
        navigate("/lcopilot/importer-dashboard/draft-lc");
      } else if (next === "supplier-docs") {
        navigate("/lcopilot/importer-dashboard/supplier-docs");
      } else if (next === "billing") {
        navigate("/lcopilot/importer-dashboard?section=billing");
      } else if (next === "settings") {
        navigate("/lcopilot/importer-dashboard?section=settings");
      }
    },
    [navigate],
  );

  return (
    <DashboardLayout
      sidebar={
        <ImporterSidebar
          activeSection={sidebarSection}
          onSectionChange={handleSectionChange}
        />
      }
    >
      <div className="container mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-bold">{config.pageTitle}</h1>
        <p className="text-muted-foreground">{config.pageDescription}</p>
      </header>

      {!extractionPayload && (
        <>
          <div className="mb-6">
            <PreparationGuide />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Upload Documents</CardTitle>
              <CardDescription>
                Accepted:{" "}
                {config.acceptedDocTypes.map((d) => d.label).join(", ")}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded p-8 text-center cursor-pointer transition-colors ${
                  isDragActive
                    ? "border-primary bg-primary/5"
                    : "border-gray-200 hover:border-primary/50"
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
                <p className="mt-2 text-sm">
                  {isDragActive
                    ? "Drop files here"
                    : "Drag PDFs here or click to select"}
                </p>
              </div>

              {files.length > 0 && (
                <ul className="space-y-1">
                  {files.map((f, i) => (
                    <li
                      key={`${f.name}-${i}`}
                      className="flex items-center gap-2 text-sm p-2 bg-secondary/20 rounded"
                    >
                      <FileText className="h-4 w-4 flex-shrink-0" />
                      <span className="flex-1 truncate">{f.name}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(i)}
                        className="h-6 w-6 p-0"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </li>
                  ))}
                </ul>
              )}

              <Button
                onClick={onStart}
                disabled={files.length === 0 || isValidating}
                size="lg"
              >
                {isValidating ? "Extracting…" : config.ctaLabel}
              </Button>
            </CardContent>
          </Card>
        </>
      )}

      {extractionPayload && jobId && (
        <ExtractionReview
          jobId={jobId}
          extractionPayload={extractionPayload}
          onStartValidation={onStartValidation}
          onBackToUpload={onBackToUpload}
        />
      )}
      </div>
    </DashboardLayout>
  );
}
