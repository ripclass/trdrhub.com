import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ValidationResults } from '@/types/lcopilot';

type Props = {
  data: ValidationResults | null;
};

const getDisplayValue = (value?: string | null): { text: string; missing: boolean } => {
  if (!value) {
    return { text: 'N/A', missing: true };
  }
  const normalized = value.toString().trim();
  if (!normalized) {
    return { text: 'N/A', missing: true };
  }
  return { text: normalized, missing: false };
};

const Field = ({ label, value }: { label: string; value?: string | null }) => {
  const { text, missing } = getDisplayValue(value);
  return (
    <div className="flex flex-col gap-1 min-w-[160px]">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="font-semibold text-foreground" title={missing ? 'Not provided in LC payload' : undefined}>
        {text}
      </span>
    </div>
  );
};

const lcTypeLabel: Record<string, string> = {
  export: 'Export LC',
  import: 'Import LC',
  standby: 'Standby LC',
  transferable: 'Transferable LC',
  unknown: 'Unknown LC',
};

// Safely convert lc_type to string - handles {types: [...]} objects from backend
const safeLcType = (value: any): string => {
  if (!value) return 'unknown';
  if (typeof value === 'string') return value;
  if (typeof value === 'object' && 'types' in value && Array.isArray(value.types)) {
    return value.types.join(', ');
  }
  return 'unknown';
};

export function LcHeader({ data }: Props) {
  const structured = data?.structured_result;
  const blocks = structured?.lc_structured?.mt700?.blocks ?? {};

  if (!structured) {
    return null;
  }

  const lcType = safeLcType(structured.lc_type);
  const typeLabel = lcTypeLabel[lcType] ?? lcType;

  const fields = [
    { label: 'LC Number', value: (blocks['20'] as string) ?? (blocks['27'] as string) },
    { label: 'LC Amount (32B)', value: blocks['32B'] as string },
    { label: 'Applicant (50)', value: blocks['50'] as string },
    { label: 'Beneficiary (59)', value: blocks['59'] as string },
    { label: 'Port of Loading (44E)', value: blocks['44E'] as string },
    { label: 'Port of Discharge (44F)', value: blocks['44F'] as string },
    { label: 'Expiry Details (31C)', value: blocks['31C'] as string },
    { label: 'Incoterm (40E)', value: blocks['40E'] as string },
  ];

  return (
    <Card className="shadow-soft border border-border/60">
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <div>
          <CardTitle className="text-lg font-semibold">Letter of Credit Overview</CardTitle>
          <p className="text-sm text-muted-foreground">Key MT700 fields extracted from the uploaded LC</p>
        </div>
        <Badge variant="outline" className="text-sm capitalize">
          {typeLabel}
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {fields.map((field) => (
          <Field key={field.label} label={field.label} value={field.value} />
        ))}
      </CardContent>
    </Card>
  );
}

export default LcHeader;

