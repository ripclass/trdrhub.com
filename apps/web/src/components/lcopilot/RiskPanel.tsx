import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, AlertTriangle, XCircle, FileCheck, Building2 } from 'lucide-react';
import type { ValidationResults } from '@/types/lcopilot';

type Props = {
  data: ValidationResults | null;
  onViewIssues?: () => void;
};

// Map risk flags to actionable messages with business impact
const FLAG_ACTIONS: Record<string, { message: string; impact: 'blocking' | 'warning' | 'info' }> = {
  missing_goods_lines: {
    message: 'Invoice missing line items from LC goods description',
    impact: 'warning',
  },
  missing_lc: {
    message: 'Letter of Credit document not uploaded',
    impact: 'blocking',
  },
  missing_invoice: {
    message: 'Commercial Invoice required for customs clearance',
    impact: 'blocking',
  },
  missing_bl: {
    message: 'Bill of Lading required for shipment release',
    impact: 'blocking',
  },
  missing_coo: {
    message: 'Certificate of Origin may be required by customs',
    impact: 'warning',
  },
  missing_insurance: {
    message: 'Insurance Certificate required if LC specifies CIF/CIP',
    impact: 'warning',
  },
  amount_mismatch: {
    message: 'Document amounts do not match LC value',
    impact: 'blocking',
  },
  date_issues: {
    message: 'Document dates may violate LC presentation period',
    impact: 'warning',
  },
};

// Determine bank submission readiness based on issues
function getBankSubmissionStatus(
  issueCount: number,
  criticalCount: number,
  riskTier?: string
): {
  status: 'ready' | 'review' | 'blocked';
  label: string;
  description: string;
  color: string;
} {
  if (criticalCount > 0 || riskTier === 'high') {
    return {
      status: 'blocked',
      label: 'Not Ready for Bank',
      description: 'Critical issues must be resolved before submission',
      color: 'bg-rose-100 text-rose-700 border-rose-200',
    };
  }
  if (issueCount > 0 || riskTier === 'med') {
    return {
      status: 'review',
      label: 'Review Required',
      description: 'Bank may issue discrepancy notice for flagged items',
      color: 'bg-amber-100 text-amber-700 border-amber-200',
    };
  }
  return {
    status: 'ready',
    label: 'Bank Ready',
    description: 'Documents appear compliant with LC terms',
    color: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  };
}

function getCustomsStatus(riskTier?: string, flags?: string[]): {
  status: 'ready' | 'review' | 'blocked';
  label: string;
  description: string;
} {
  const blockingFlags = (flags || []).filter(
    (f) => FLAG_ACTIONS[f]?.impact === 'blocking'
  );
  
  if (blockingFlags.length > 0) {
    return {
      status: 'blocked',
      label: 'Missing Documents',
      description: 'Required documents for customs not present',
    };
  }
  if (riskTier === 'high') {
    return {
      status: 'review',
      label: 'Review Advised',
      description: 'Customs may request additional documentation',
    };
  }
  return {
    status: 'ready',
    label: 'Customs Ready',
    description: 'Core documents present for clearance',
  };
}

export function RiskPanel({ data, onViewIssues }: Props) {
  const risk = data?.structured_result?.analytics?.customs_risk;
  const analytics = data?.structured_result?.analytics;
  const issues = data?.structured_result?.issues || [];
  
  // Count issues by severity
  const criticalCount = issues.filter(
    (i: any) => i.severity?.toLowerCase() === 'critical'
  ).length;
  const totalIssues = issues.length;

  // Get statuses
  const bankStatus = getBankSubmissionStatus(totalIssues, criticalCount, risk?.tier);
  const customsStatus = getCustomsStatus(risk?.tier, risk?.flags);

  // Get actionable flags
  const actionableFlags = (risk?.flags || []).map((flag: string) => {
    const action = FLAG_ACTIONS[flag];
    return {
      flag,
      message: action?.message || flag.replace(/_/g, ' '),
      impact: action?.impact || 'info',
    };
  });

  const StatusIcon = {
    ready: CheckCircle2,
    review: AlertTriangle,
    blocked: XCircle,
  };

  const BankIcon = StatusIcon[bankStatus.status];
  const CustomsIcon = StatusIcon[customsStatus.status];

  return (
    <Card className="shadow-soft border border-border/60">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold">Submission Readiness</CardTitle>
        <p className="text-sm text-muted-foreground">
          Assessment for bank presentation and customs clearance
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Two-column readiness indicators */}
        <div className="grid grid-cols-2 gap-3">
          {/* Bank Submission Status */}
          <div className={`rounded-lg border p-3 ${bankStatus.color}`}>
            <div className="flex items-center gap-2 mb-1">
              <Building2 className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Bank</span>
            </div>
            <div className="flex items-center gap-2">
              <BankIcon className="w-5 h-5" />
              <span className="font-semibold">{bankStatus.label}</span>
            </div>
            <p className="text-xs mt-1 opacity-80">{bankStatus.description}</p>
          </div>

          {/* Customs Status */}
          <div className={`rounded-lg border p-3 ${
            customsStatus.status === 'ready' 
              ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
              : customsStatus.status === 'review'
              ? 'bg-amber-100 text-amber-700 border-amber-200'
              : 'bg-rose-100 text-rose-700 border-rose-200'
          }`}>
            <div className="flex items-center gap-2 mb-1">
              <FileCheck className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Customs</span>
            </div>
            <div className="flex items-center gap-2">
              <CustomsIcon className="w-5 h-5" />
              <span className="font-semibold">{customsStatus.label}</span>
            </div>
            <p className="text-xs mt-1 opacity-80">{customsStatus.description}</p>
          </div>
        </div>

        {/* Actionable Items - Clickable to view issues */}
        {actionableFlags.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-semibold text-foreground">Action Items</p>
            <div className="space-y-2">
              {actionableFlags.map((item, idx) => (
                <button
                  key={`${item.flag}-${idx}`}
                  onClick={onViewIssues}
                  className={`w-full flex items-start gap-2 p-2 rounded-md text-sm text-left transition-all hover:shadow-md cursor-pointer ${
                    item.impact === 'blocking'
                      ? 'bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100'
                      : item.impact === 'warning'
                      ? 'bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100'
                      : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {item.impact === 'blocking' ? (
                    <XCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  ) : item.impact === 'warning' ? (
                    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <span>{item.message}</span>
                  </div>
                  {item.impact === 'blocking' && (
                    <span className="text-xs font-semibold bg-rose-600 text-white px-2 py-0.5 rounded hover:bg-rose-700">
                      Fix Now →
                    </span>
                  )}
                  {item.impact === 'warning' && (
                    <span className="text-xs font-semibold bg-amber-500 text-white px-2 py-0.5 rounded hover:bg-amber-600">
                      Review →
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {actionableFlags.length === 0 && (
          <div className="flex items-center gap-2 p-3 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-5 h-5" />
            <span className="text-sm font-medium">All document checks passed</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default RiskPanel;

