import { useEffect, useMemo, useState, type ChangeEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  FileText,
  Loader2,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { useResumeValidate, type ExtractionReadyDocument, type ExtractionReadyResponse } from '@/hooks/use-lcopilot';
import { useToast } from '@/hooks/use-toast';

interface ExtractionReviewProps {
  jobId?: string;
  extractionPayload?: ExtractionReadyResponse | null;
  lcNumber?: string;
  onStartValidation?: (payload: { jobId: string; lcNumber?: string }) => void;
  onBackToUpload?: () => void;
}

interface DocSectionState {
  docKey: string;
  filename: string;
  documentType: string;
  fields: FieldState[];
}

interface FieldState {
  name: string;
  label: string;
  currentValue: string;
  aiGuess: string;
  isEmpty: boolean;
  isConfirmed: boolean;
}

const FRIENDLY_FIELD_LABELS: Record<string, string> = {
  lc_number: 'LC Number',
  buyer_purchase_order_number: 'Buyer Purchase Order #',
  purchase_order_number: 'Purchase Order #',
  po_number: 'Purchase Order #',
  exporter_bin: 'Exporter BIN',
  exporter_tin: 'Exporter TIN',
  issue_date: 'Issue Date',
  expiry_date: 'Expiry Date',
  latest_shipment_date: 'Latest Shipment Date',
  applicant: 'Applicant',
  beneficiary: 'Beneficiary',
  amount: 'Amount',
  currency: 'Currency',
  port_of_loading: 'Port of Loading',
  port_of_discharge: 'Port of Discharge',
  goods_description: 'Goods Description',
  invoice_number: 'Invoice Number',
  invoice_date: 'Invoice Date',
  seller: 'Seller',
  buyer: 'Buyer',
  bl_number: 'BL Number',
  shipper: 'Shipper',
  consignee: 'Consignee',
  vessel_name: 'Vessel Name',
  voyage_number: 'Voyage Number',
  gross_weight: 'Gross Weight',
  net_weight: 'Net Weight',
  total_packages: 'Total Packages',
  country_of_origin: 'Country of Origin',
  certificate_number: 'Certificate Number',
};

function humanizeFieldName(name: string): string {
  if (FRIENDLY_FIELD_LABELS[name]) {
    return FRIENDLY_FIELD_LABELS[name];
  }
  return name
    .split('_')
    .map((s) => (s.length ? s[0].toUpperCase() + s.slice(1) : s))
    .join(' ');
}

function humanizeDocType(docType: string): string {
  return docType
    .split('_')
    .map((s) => (s.length ? s[0].toUpperCase() + s.slice(1) : s))
    .join(' ');
}

function coerceToString(value: any): string {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

// Canonical field name -> list of legacy alias names the vision LLM (or
// older regex parsers) sometimes return. When the canonical key is empty
// on the extracted_fields dict, we fall back to the first populated alias.
// The backend's _canonicalize_field_names() should handle this upstream, but
// this mapping is the frontend's safety net in case the backend deploy lags
// or an older extractor path is used.
const FIELD_ALIAS_MAP: Record<string, string[]> = {
  seller: ['seller_name', 'exporter', 'exporter_name', 'shipper'],
  buyer: ['buyer_name', 'importer', 'importer_name', 'consignee', 'applicant'],
  lc_number: ['lc_reference', 'documentary_credit_number', 'credit_number', 'number'],
  buyer_purchase_order_number: ['buyer_po_number', 'po_number', 'purchase_order_number', 'buyer_po'],
  exporter_bin: ['bin', 'bin_number', 'exporter_bin_number', 'seller_bin'],
  exporter_tin: ['tin', 'tin_number', 'exporter_tin_number', 'seller_tin'],
  exporter: ['exporter_name', 'seller', 'seller_name'],
  issuing_authority: ['certifying_authority', 'authority', 'issuer'],
  size_breakdown: ['packing_size_breakdown', 'sizes', 'size_distribution'],
  total_packages: ['number_of_packages', 'total_cartons', 'carton_count', 'packages'],
  applicant: ['buyer', 'buyer_name', 'importer'],
  beneficiary: ['seller', 'seller_name', 'exporter', 'exporter_name', 'insured_party'],
  country_of_origin: ['origin_country', 'country'],
  bl_number: ['bill_of_lading_number'],
  inspection_agency: ['inspector', 'inspection_company'],
  issuer: ['insurance_company', 'issuing_bank'],
  // MT700 LC field aliases — vision LLM consistently returns these legacy
  // names even though the new schemas ask for the canonical ones.
  form_of_documentary_credit: ['lc_type', 'form_of_doc_credit', 'credit_form'],
  applicable_rules: ['ucp_reference', 'rules', 'applicable_uniform_rules'],
  drafts_at: ['payment_terms', 'tenor', 'usance'],
  available_by: ['available_with_method'],
};

function readAliasedValue(extracted: Record<string, any>, fieldName: string): any {
  // Canonical name wins if populated.
  const canonical = extracted[fieldName];
  if (canonical != null && canonical !== '' && canonical !== null) return canonical;
  const aliases = FIELD_ALIAS_MAP[fieldName];
  if (!aliases) return canonical; // null/empty fall-through
  for (const alias of aliases) {
    const v = extracted[alias];
    if (v != null && v !== '') return v;
  }
  return canonical;
}

// Field names whose values are typically long-form text (paragraphs, lists,
// free-text rule descriptions). These render in a textarea instead of a
// single-line input AND span both columns of the grid so the user can
// actually read what was extracted.
const LONG_FORM_FIELD_NAMES = new Set<string>([
  'goods_description',
  'description_of_goods',
  'documents_required',
  'additional_conditions',
  'special_conditions',
  'attestation_text',
  'inspection_result',
  'quality_finding',
  'analysis_result',
  'marks_and_numbers',
  'payment_terms',
  'instructions_to_paying_bank',
  'risks_covered',
  'voyage_details',
  'transport_mode_chain',
  'charges',
]);

// Heuristic: even if the field name isn't in the set above, if the AI
// returned a value with a newline OR a length > 80 chars, render it as
// a textarea so the user can actually read it.
function shouldRenderAsTextarea(fieldName: string, value: string): boolean {
  if (LONG_FORM_FIELD_NAMES.has(fieldName)) return true;
  if (!value) return false;
  if (value.length > 80) return true;
  if (value.includes('\n')) return true;
  return false;
}

// Pretty-format a value for display. Lists / objects come back from the
// extractor as Python repr strings or JSON; turn them into one-per-line
// human-readable text.
function prettyFormatLongValue(value: string): string {
  if (!value) return '';
  // Python list repr: "['item one', 'item two']" -> "item one\nitem two"
  if (value.startsWith("['") && value.endsWith("']")) {
    try {
      // Convert single-quoted Python list to JSON array
      const jsonish = value
        .replace(/^\['/, '["')
        .replace(/'\]$/, '"]')
        .replace(/', '/g, '", "');
      const arr = JSON.parse(jsonish);
      if (Array.isArray(arr)) return arr.map((s, i) => `${i + 1}. ${s}`).join('\n');
    } catch {
      /* fall through */
    }
  }
  // JSON array
  if (value.startsWith('[') && value.endsWith(']')) {
    try {
      const arr = JSON.parse(value);
      if (Array.isArray(arr)) return arr.map((s, i) => `${i + 1}. ${s}`).join('\n');
    } catch {
      /* fall through */
    }
  }
  return value;
}

function buildDocSectionState(
  doc: ExtractionReadyDocument,
  requiredFields: string[],
): DocSectionState {
  const extracted = (doc.extracted_fields || doc.extractedFields || {}) as Record<string, any>;
  const filename = (doc.filename || doc.name || 'document') as string;
  const documentType = (doc.document_type || doc.documentType || 'unknown') as string;
  const docKey = (doc.id || doc.document_id || filename) as string;

  const fields: FieldState[] = requiredFields.map((fieldName) => {
    const rawValue = readAliasedValue(extracted, fieldName);
    const stringified = coerceToString(rawValue);
    // Long-form fields (goods_description, documents_required, etc.) come
    // back as Python list reprs or paragraphs. Pretty-print them so the
    // textarea is actually readable.
    const currentValue = LONG_FORM_FIELD_NAMES.has(fieldName)
      ? prettyFormatLongValue(stringified)
      : stringified;
    return {
      name: fieldName,
      label: humanizeFieldName(fieldName),
      currentValue,
      aiGuess: currentValue,
      isEmpty: !currentValue.trim(),
      isConfirmed: false,
    };
  });

  return { docKey, filename, documentType, fields };
}

export function ExtractionReview({
  jobId: propJobId,
  extractionPayload,
  lcNumber,
  onStartValidation,
  onBackToUpload,
}: ExtractionReviewProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const { resumeValidate, isLoading: isStartingValidation } = useResumeValidate();

  // Read the extraction payload from props first, then from navigation state
  // (upload page passes it via navigate(..., { state: { extraction: ... } })).
  const stateExtraction = (location.state as any)?.extraction as ExtractionReadyResponse | undefined;
  const payload = extractionPayload ?? stateExtraction ?? null;
  const jobId = propJobId ?? payload?.jobId ?? payload?.job_id ?? null;

  const [docSections, setDocSections] = useState<DocSectionState[]>([]);

  useEffect(() => {
    if (!payload) {
      setDocSections([]);
      return;
    }
    const byType = payload.required_fields?.by_document_type || {};
    const baseline = payload.required_fields?.baseline_required || [];
    const lcSelfRequired =
      (payload.required_fields as any)?.lc_self_required || [];
    const built = (payload.documents || []).map((doc) => {
      const docType = String(doc.document_type || doc.documentType || '');
      // LC uses the MT700 mandatory list, NOT the cross-doc applies_to_all
      // set. The LC is the SOURCE of those cross-doc requirements, not a
      // doc that must satisfy them.
      const isLC = docType === 'letter_of_credit' || docType === 'swift_message' || docType === 'lc_application';
      if (isLC && Array.isArray(lcSelfRequired) && lcSelfRequired.length > 0) {
        return buildDocSectionState(doc, lcSelfRequired);
      }
      const forType = byType[docType];
      const required = Array.isArray(forType) && forType.length > 0 ? forType : baseline;
      return buildDocSectionState(doc, required);
    });
    setDocSections(built);
  }, [payload]);

  const totalRequired = useMemo(
    () => docSections.reduce((n, s) => n + s.fields.length, 0),
    [docSections],
  );
  const totalEmpty = useMemo(
    () => docSections.reduce((n, s) => n + s.fields.filter((f) => f.isEmpty).length, 0),
    [docSections],
  );
  const totalFilled = totalRequired - totalEmpty;

  const handleFieldChange =
    (docIdx: number, fieldIdx: number) =>
    (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const nextValue = e.target.value;
      setDocSections((prev) => {
        const next = [...prev];
        const section = { ...next[docIdx] };
        const fields = [...section.fields];
        fields[fieldIdx] = {
          ...fields[fieldIdx],
          currentValue: nextValue,
          isEmpty: !nextValue.trim(),
          isConfirmed: fields[fieldIdx].aiGuess === nextValue ? fields[fieldIdx].isConfirmed : true,
        };
        section.fields = fields;
        next[docIdx] = section;
        return next;
      });
    };

  const buildFieldOverrides = (): Record<string, Record<string, any>> => {
    const overrides: Record<string, Record<string, any>> = {};
    for (const section of docSections) {
      const changed: Record<string, any> = {};
      for (const field of section.fields) {
        if (field.currentValue !== field.aiGuess) {
          changed[field.name] = field.currentValue;
        }
      }
      if (Object.keys(changed).length > 0) {
        overrides[section.docKey] = changed;
      }
    }
    return overrides;
  };

  const handleStartValidation = async () => {
    if (!jobId) {
      toast({
        title: 'Missing job',
        description: 'Cannot start validation without a job id.',
        variant: 'destructive',
      });
      return;
    }

    try {
      const fieldOverrides = buildFieldOverrides();
      toast({
        title: 'Starting validation',
        description: 'Applying your confirmed fields and running the validation pipeline…',
      });
      await resumeValidate({ jobId, fieldOverrides });

      if (onStartValidation) {
        onStartValidation({ jobId, lcNumber });
      } else {
        const params = new URLSearchParams({ section: 'reviews', jobId });
        if (lcNumber) params.set('lc', lcNumber);
        navigate(`/lcopilot/exporter-dashboard?${params.toString()}`);
      }
    } catch (err: any) {
      toast({
        title: 'Validation failed to start',
        description: err?.message || 'Could not resume validation. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleBack = () => {
    if (onBackToUpload) {
      onBackToUpload();
      return;
    }
    navigate('/lcopilot/exporter-dashboard?section=upload');
  };

  if (!payload) {
    return (
      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-amber-500" />
            Extraction review unavailable
          </CardTitle>
          <CardDescription>
            We couldn't find an active extraction session. Please re-upload your documents.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleBack} variant="outline">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to upload
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <Card className="shadow-soft border-0">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-blue-500" />
                Review Extracted Fields
              </CardTitle>
              <CardDescription>
                Confirm or correct the fields required by this LC before validation runs.
                Only the fields the LC actually asks for are shown below.
              </CardDescription>
            </div>
            <Button onClick={handleBack} variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to upload
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3 rounded-lg border bg-card p-4">
              <FileText className="w-5 h-5 text-slate-500" />
              <div>
                <p className="text-sm text-muted-foreground">Documents</p>
                <p className="text-2xl font-semibold">{docSections.length}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border bg-card p-4">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <div>
                <p className="text-sm text-muted-foreground">Fields Populated</p>
                <p className="text-2xl font-semibold">
                  {totalFilled} <span className="text-base text-muted-foreground">/ {totalRequired}</span>
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border bg-card p-4">
              <AlertCircle className={`w-5 h-5 ${totalEmpty > 0 ? 'text-amber-500' : 'text-slate-400'}`} />
              <div>
                <p className="text-sm text-muted-foreground">Need Your Input</p>
                <p className="text-2xl font-semibold">{totalEmpty}</p>
              </div>
            </div>
          </div>
          {totalEmpty > 0 && (
            <Alert className="mt-4 border-amber-500/30 bg-amber-50 dark:bg-amber-950/20">
              <AlertCircle className="w-4 h-4 text-amber-500" />
              <AlertTitle>Please fill {totalEmpty} missing field{totalEmpty === 1 ? '' : 's'}</AlertTitle>
              <AlertDescription>
                The AI couldn't find the highlighted values in your uploaded files. Enter them
                directly so validation has a reliable field set to check against.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Per-document review sections */}
      {docSections.map((section, docIdx) => {
        const emptyCount = section.fields.filter((f) => f.isEmpty).length;
        return (
          <Card key={`${section.docKey}-${docIdx}`} className="shadow-soft border-0">
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <FileText className="w-4 h-4" />
                    {section.filename}
                  </CardTitle>
                  <CardDescription>
                    <Badge variant="secondary" className="mr-2">
                      {humanizeDocType(section.documentType)}
                    </Badge>
                    {section.fields.length} required field{section.fields.length === 1 ? '' : 's'}
                    {emptyCount > 0 && (
                      <span className="text-amber-600 ml-2">
                        ({emptyCount} missing)
                      </span>
                    )}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {section.fields.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No required fields on this document.
                </p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {section.fields.map((field, fieldIdx) => {
                    const isLongForm = shouldRenderAsTextarea(field.name, field.currentValue);
                    // Long fields span both columns so the textarea is wide
                    // enough to actually read clauses/lists.
                    const wrapperClass = isLongForm
                      ? 'space-y-1 md:col-span-2'
                      : 'space-y-1';
                    // Roughly size the textarea to the content — clamped to
                    // a sane min/max so it doesn't dwarf the page.
                    const contentLineCount = (field.currentValue.match(/\n/g)?.length ?? 0) + 1;
                    const textareaRows = Math.min(Math.max(contentLineCount + 1, 4), 16);
                    return (
                      <div key={`${section.docKey}-${field.name}-${fieldIdx}`} className={wrapperClass}>
                        <Label htmlFor={`${section.docKey}-${field.name}`} className="flex items-center gap-2">
                          {field.label}
                          {field.isEmpty && (
                            <Badge variant="outline" className="text-amber-600 border-amber-500/40 text-[10px]">
                              Missing
                            </Badge>
                          )}
                          {!field.isEmpty && !field.isConfirmed && (
                            <Badge variant="outline" className="text-slate-500 border-slate-300 text-[10px]">
                              AI extracted
                            </Badge>
                          )}
                          {field.isConfirmed && (
                            <Badge variant="outline" className="text-emerald-600 border-emerald-500/40 text-[10px]">
                              You edited
                            </Badge>
                          )}
                        </Label>
                        {isLongForm ? (
                          <Textarea
                            id={`${section.docKey}-${field.name}`}
                            value={field.currentValue}
                            onChange={handleFieldChange(docIdx, fieldIdx)}
                            placeholder={field.isEmpty ? 'Enter value from document…' : undefined}
                            rows={textareaRows}
                            className={
                              (field.isEmpty ? 'border-amber-500/40 ' : '') +
                              'font-mono text-sm leading-relaxed resize-y'
                            }
                          />
                        ) : (
                          <Input
                            id={`${section.docKey}-${field.name}`}
                            value={field.currentValue}
                            onChange={handleFieldChange(docIdx, fieldIdx)}
                            placeholder={field.isEmpty ? 'Enter value from document…' : undefined}
                            className={field.isEmpty ? 'border-amber-500/40' : undefined}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}

      <Separator />

      {/* Start validation action bar */}
      <Card className="shadow-soft border-0">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-6 h-6 text-blue-500" />
              <div>
                <p className="font-medium">Ready to validate?</p>
                <p className="text-sm text-muted-foreground">
                  {totalEmpty === 0
                    ? 'All required fields are filled in. Validation will run on the confirmed set.'
                    : `${totalEmpty} field${totalEmpty === 1 ? '' : 's'} still missing — validation runs on what you have.`}
                </p>
              </div>
            </div>
            <Button
              onClick={handleStartValidation}
              disabled={isStartingValidation || !jobId}
              className="min-w-[180px]"
            >
              {isStartingValidation ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Starting…
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4 mr-2" />
                  Start Validation
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default ExtractionReview;
