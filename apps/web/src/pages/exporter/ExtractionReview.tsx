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
  /** LC-only: tag values (e.g. "IRREVOCABLE") shown as badges in the header. */
  headerBadges?: { label: string; value: string }[];
  /** LC-only: how many of `fields` are the required-section split point.
   *  fields[0..requiredCount] = required, fields[requiredCount..] = optional. */
  requiredCount?: number;
  /** True for the LC's own section so we render it differently. */
  isLetterOfCredit?: boolean;
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

// LC review categorization (the LC is the source-of-truth document, so its
// review screen needs to be different from supporting docs).
//
// HIDDEN: never shown to the user. Either trivial metadata or operational
// concerns that don't drive validation outcomes.
const LC_HIDDEN_FIELDS = new Set<string>([
  'sequence_of_total',         // Field 27 — only matters if "1/1" is wrong, then we'd error elsewhere
  'applicable_rules',          // Field 40E — engine-internal (UCP600 / ISP98 / etc.)
  'available_with',            // Field 41a — bank operational, doesn't drive doc compliance
  'available_by',              // Field 41a method — same
  'drafts_at',                 // Field 42C — only matters if drafts are presented
  'drawee',                    // Field 42a — same
  'confirmation_instructions', // Field 49 — bank-to-bank
  'instructions_to_paying_bank', // Field 78 — bank-to-bank
  'amount_tolerance',          // Field 39A — handled by validation engine
  'period_for_presentation',   // Field 48 — only matters when overrides 21-day default
]);

// HEADER: shown as a badge on the LC card header instead of as an editable
// field. These tag the LC's "type" rather than asking the user to confirm a
// value.
const LC_HEADER_FIELDS = new Set<string>([
  'form_of_documentary_credit',
]);

// REQUIRED: the 8 skeleton fields a bank examiner needs to validate.
// Without these the system cannot run validation at all.
const LC_REQUIRED_FIELDS = [
  'lc_number',
  'amount',
  'currency',
  'beneficiary',
  'applicant',
  'goods_description',
  'documents_required',
  'expiry_date',
  'latest_shipment_date',
];

// OPTIONAL: useful but not deal-breakers. Shown in a separate section.
const LC_OPTIONAL_FIELDS = [
  'expiry_place',
  'port_of_loading',
  'port_of_discharge',
  'additional_conditions',
  'partial_shipments',  // Field 43P
  'transshipment',      // Field 43T
  'issue_date',
  'charges',
];

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

function buildFieldState(fieldName: string, extracted: Record<string, any>): FieldState {
  const rawValue = readAliasedValue(extracted, fieldName);
  const stringified = coerceToString(rawValue);
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
}

function buildDocSectionState(
  doc: ExtractionReadyDocument,
  requiredFields: string[],
): DocSectionState {
  const extracted = (doc.extracted_fields || doc.extractedFields || {}) as Record<string, any>;
  const filename = (doc.filename || doc.name || 'document') as string;
  const documentType = (doc.document_type || doc.documentType || 'unknown') as string;
  const docKey = (doc.id || doc.document_id || filename) as string;

  const fields: FieldState[] = requiredFields.map((fieldName) => buildFieldState(fieldName, extracted));

  return { docKey, filename, documentType, fields };
}

/** LC-specific builder.
 *
 * Splits the LC's fields into:
 *   - Header badges (form_of_documentary_credit etc.)
 *   - Required section (8 skeleton fields)
 *   - Optional section (only fields that have values OR are conditionally relevant)
 *
 * Hidden fields (LC_HIDDEN_FIELDS) are dropped entirely.
 */
function buildLCDocSectionState(doc: ExtractionReadyDocument): DocSectionState {
  const extracted = (doc.extracted_fields || doc.extractedFields || {}) as Record<string, any>;
  const filename = (doc.filename || doc.name || 'document') as string;
  const documentType = (doc.document_type || doc.documentType || 'unknown') as string;
  const docKey = (doc.id || doc.document_id || filename) as string;

  // Header badges — pull values from the extracted dict, only show if populated
  const headerBadges: { label: string; value: string }[] = [];
  for (const fieldName of LC_HEADER_FIELDS) {
    const value = coerceToString(readAliasedValue(extracted, fieldName));
    if (value.trim()) {
      headerBadges.push({ label: humanizeFieldName(fieldName), value });
    }
  }

  // Required section (always shown)
  const requiredFields: FieldState[] = LC_REQUIRED_FIELDS.map((fieldName) =>
    buildFieldState(fieldName, extracted),
  );

  // Optional section — only show fields the AI actually populated. The
  // user shouldn't be confronted with empty inputs for fields that don't
  // typically appear or aren't relevant to validation.
  const optionalFields: FieldState[] = LC_OPTIONAL_FIELDS
    .map((fieldName) => buildFieldState(fieldName, extracted))
    .filter((f) => !f.isEmpty);

  return {
    docKey,
    filename,
    documentType,
    fields: [...requiredFields, ...optionalFields],
    headerBadges,
    requiredCount: requiredFields.length,
    isLetterOfCredit: true,
  };
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
  const [missingDocsAcknowledged, setMissingDocsAcknowledged] = useState<boolean>(false);

  // Reset the acknowledgement whenever the set of missing docs changes so the
  // user sees the warning again if they come back after uploading more files.
  useEffect(() => {
    setMissingDocsAcknowledged(false);
  }, [payload?.missing_required_documents?.map((m) => m.type).join(',')]);

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
      // LC uses a dedicated builder that splits fields into header
      // badges + required section + optional section, and HIDES fields
      // that aren't user-relevant (40E applicable_rules, 27 sequence,
      // 41a available_with/by, 49 confirmation, etc.).
      const isLC = docType === 'letter_of_credit' || docType === 'swift_message' || docType === 'lc_application';
      if (isLC) {
        return buildLCDocSectionState(doc);
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

  const hasUnacknowledgedMissingDocs =
    Array.isArray(payload?.missing_required_documents) &&
    payload!.missing_required_documents!.length > 0 &&
    !missingDocsAcknowledged;

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
          {Array.isArray(payload.missing_required_documents) &&
            payload.missing_required_documents.length > 0 &&
            !missingDocsAcknowledged && (
              <Alert className="mt-4 border-red-500/40 bg-red-50 dark:bg-red-950/20">
                <AlertCircle className="w-4 h-4 text-red-600" />
                <AlertTitle>
                  Your LC requires {payload.missing_required_documents.length}{' '}
                  document{payload.missing_required_documents.length === 1 ? '' : 's'} you haven't uploaded
                </AlertTitle>
                <AlertDescription className="space-y-3">
                  <ul className="list-disc pl-5 text-sm space-y-1 mt-2">
                    {payload.missing_required_documents.map((m, i) => (
                      <li key={`${m.type}-${i}`}>
                        <span className="font-medium">{m.display_name || m.type}</span>
                        {m.raw_text ? (
                          <span className="text-muted-foreground"> — {m.raw_text}</span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                  <p className="text-sm">
                    You can validate without these, but the engine will flag them as missing on
                    the results page. If you have them, go back and upload; otherwise acknowledge
                    below to continue.
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleBack}
                    >
                      <ArrowLeft className="w-4 h-4 mr-2" />
                      Upload missing documents
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setMissingDocsAcknowledged(true)}
                    >
                      Continue without them
                    </Button>
                  </div>
                </AlertDescription>
              </Alert>
            )}
        </CardContent>
      </Card>

      {/* Per-document review sections */}
      {docSections.map((section, docIdx) => {
        const emptyCount = section.fields.filter((f) => f.isEmpty).length;
        const renderFieldEntry = (field: FieldState, fieldIdx: number) => {
          const isLongForm = shouldRenderAsTextarea(field.name, field.currentValue);
          const wrapperClass = isLongForm
            ? 'space-y-1 md:col-span-2'
            : 'space-y-1';
          const contentLineCount = (field.currentValue.match(/\n/g)?.length ?? 0) + 1;
          const textareaRows = Math.min(Math.max(contentLineCount + 1, 4), 16);
          return (
            <div key={`${section.docKey}-${field.name}-${fieldIdx}`} className={wrapperClass}>
              <Label htmlFor={`${section.docKey}-${field.name}`} className="flex items-center gap-2">
                {field.label}
                {field.isEmpty && (
                  <Badge
                    variant="outline"
                    className="text-amber-600 border-amber-500/40 text-[10px]"
                    title="Not found on your document. The LC requires this field — if you continue without filling it, the bank will flag this as a discrepancy on the results page."
                  >
                    Not on document — LC requires this
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
                  placeholder={field.isEmpty ? 'Type the value if it exists on your document — otherwise leave blank and validation will flag it.' : undefined}
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
                  placeholder={field.isEmpty ? 'Type the value if it exists on your document — otherwise leave blank and validation will flag it.' : undefined}
                  className={field.isEmpty ? 'border-amber-500/40' : undefined}
                />
              )}
            </div>
          );
        };

        // LC card has a 2-section layout (required + optional) AND header
        // badges; supporting docs render as a single flat grid.
        const isLC = !!section.isLetterOfCredit;
        const requiredFields = isLC && section.requiredCount != null
          ? section.fields.slice(0, section.requiredCount)
          : section.fields;
        const optionalFields = isLC && section.requiredCount != null
          ? section.fields.slice(section.requiredCount)
          : [];
        const requiredEmptyCount = requiredFields.filter((f) => f.isEmpty).length;

        return (
          <Card key={`${section.docKey}-${docIdx}`} className="shadow-soft border-0">
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <FileText className="w-4 h-4" />
                    {section.filename}
                  </CardTitle>
                  <CardDescription className="mt-1 flex items-center gap-2 flex-wrap">
                    <Badge variant="secondary">
                      {humanizeDocType(section.documentType)}
                    </Badge>
                    {/* LC-only header badges (40A form_of_documentary_credit etc.) */}
                    {section.headerBadges?.map((b) => (
                      <Badge
                        key={b.label}
                        variant="outline"
                        className="border-blue-500/40 text-blue-700 dark:text-blue-300"
                      >
                        {b.value}
                      </Badge>
                    ))}
                    <span className="text-xs text-muted-foreground">
                      {isLC
                        ? `${requiredFields.length} required field${requiredFields.length === 1 ? '' : 's'}`
                        : `${section.fields.length} required field${section.fields.length === 1 ? '' : 's'}`}
                      {(isLC ? requiredEmptyCount : emptyCount) > 0 && (
                        <span className="text-amber-600 ml-1">
                          ({(isLC ? requiredEmptyCount : emptyCount)} missing)
                        </span>
                      )}
                    </span>
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {section.fields.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No required fields on this document.
                </p>
              ) : isLC ? (
                <div className="space-y-6">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-3">
                      Required fields
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {requiredFields.map((field, fieldIdx) => renderFieldEntry(field, fieldIdx))}
                    </div>
                  </div>
                  {optionalFields.length > 0 && (
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-3">
                        Additional details (optional, AI auto-extracted)
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {optionalFields.map((field, fieldIdx) =>
                          renderFieldEntry(field, (section.requiredCount ?? 0) + fieldIdx),
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {section.fields.map((field, fieldIdx) => renderFieldEntry(field, fieldIdx))}
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
                  {hasUnacknowledgedMissingDocs
                    ? `${payload?.missing_required_documents?.length ?? 0} required document${(payload?.missing_required_documents?.length ?? 0) === 1 ? '' : 's'} missing — acknowledge the warning above to continue.`
                    : totalEmpty === 0
                    ? 'All required fields are filled in. Validation will run on the confirmed set.'
                    : `${totalEmpty} field${totalEmpty === 1 ? '' : 's'} still missing — validation runs on what you have.`}
                </p>
              </div>
            </div>
            <Button
              onClick={handleStartValidation}
              disabled={isStartingValidation || !jobId || hasUnacknowledgedMissingDocs}
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
