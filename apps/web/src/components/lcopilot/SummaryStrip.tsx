import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ValidationResults } from '@/types/lcopilot';

type Props = {
  data: ValidationResults | null;
};

const formatNumber = (value?: number | null) => (typeof value === 'number' && !Number.isNaN(value) ? value : 0);

export function SummaryStrip({ data }: Props) {
  const structured = data?.structured_result;
  const summary = structured?.processing_summary;
  const analytics = structured?.analytics;

  if (!structured || !summary) {
    return null;
  }

  const documentsProcessed =
    analytics?.documents_processed ?? summary.total_documents ?? data?.documents?.length ?? 0;
  const statusDistribution = analytics?.document_status_distribution ?? {};
  const severityBreakdown = summary.severity_breakdown ?? {};
  const processingTime =
    summary.processing_time_display ?? analytics?.processing_time_display ?? 'N/A';

  const infoBlocks = [
    {
      label: 'Documents',
      value: documentsProcessed,
      helper: `${formatNumber(statusDistribution.success)} success / ${formatNumber(
        statusDistribution.warning,
      )} warning / ${formatNumber(statusDistribution.error)} error`,
    },
    {
      label: 'Processing Time',
      value: processingTime,
      helper: 'Wall-clock time',
    },
    {
      label: 'Issues',
      value: summary.total_issues ?? 0,
      helper: `${formatNumber(severityBreakdown.critical)} critical - ${formatNumber(
        severityBreakdown.major,
      )} major - ${formatNumber(severityBreakdown.medium)} medium`,
    },
  ];

  return (
    <Card className="shadow-soft border border-border/60 h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold">Processing Summary</CardTitle>
        <p className="text-sm text-muted-foreground">Snapshot of extraction health</p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        {infoBlocks.map((block) => (
          <div key={block.label} className="flex-1 border-l border-border/40 pl-4 first:border-none first:pl-0">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{block.label}</p>
            <p className="text-2xl font-semibold text-foreground">
              {typeof block.value === 'number' && !Number.isNaN(block.value) ? block.value : block.value}
            </p>
            <p className="text-xs text-muted-foreground">{block.helper}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default SummaryStrip;

