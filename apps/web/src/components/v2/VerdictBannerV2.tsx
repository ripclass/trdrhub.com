/**
 * V2 Verdict Banner
 * 
 * Shows the bank submission verdict prominently.
 */

import { 
  CheckCircle, 
  AlertTriangle, 
  Pause, 
  XCircle,
  ArrowRight,
  Clock,
  DollarSign,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

export interface VerdictV2 {
  status: 'SUBMIT' | 'CAUTION' | 'HOLD' | 'REJECT';
  message: string;
  recommendation: string;
  confidence: number;
  canSubmitToBank: boolean;
  willBeRejected: boolean;
  estimatedDiscrepancyFee: number;
  issueSummary: {
    critical: number;
    major: number;
    minor: number;
    info: number;
    total: number;
  };
  actionItems: Array<{
    priority: string;
    issue: string;
    action: string;
  }>;
}

interface VerdictBannerV2Props {
  verdict: VerdictV2;
  processingTime: number;
  onSubmit?: () => void;
}

const verdictConfig = {
  SUBMIT: {
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-300',
    gradientFrom: 'from-green-500',
    gradientTo: 'to-emerald-500',
    label: 'Ready to Submit',
  },
  CAUTION: {
    icon: AlertTriangle,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-300',
    gradientFrom: 'from-yellow-500',
    gradientTo: 'to-orange-500',
    label: 'Caution',
  },
  HOLD: {
    icon: Pause,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-300',
    gradientFrom: 'from-orange-500',
    gradientTo: 'to-red-500',
    label: 'Hold',
  },
  REJECT: {
    icon: XCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-300',
    gradientFrom: 'from-red-500',
    gradientTo: 'to-rose-600',
    label: 'Will Be Rejected',
  },
};

export function VerdictBannerV2({ verdict, processingTime, onSubmit }: VerdictBannerV2Props) {
  const config = verdictConfig[verdict.status];
  const Icon = config.icon;
  
  return (
    <div className={cn(
      'rounded-xl border-2 overflow-hidden',
      config.borderColor,
      config.bgColor,
    )}>
      {/* Gradient Header */}
      <div className={cn(
        'bg-gradient-to-r py-4 px-6',
        config.gradientFrom,
        config.gradientTo,
      )}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 text-white">
            <Icon className="h-8 w-8" />
            <div>
              <p className="text-sm font-medium opacity-90">Bank Verdict</p>
              <h2 className="text-2xl font-bold">{config.label}</h2>
            </div>
          </div>
          
          <div className="text-right text-white">
            <div className="flex items-center gap-2 text-sm opacity-90">
              <Clock className="h-4 w-4" />
              <span>{processingTime.toFixed(1)}s</span>
            </div>
            <p className="text-sm font-medium">
              {Math.round(verdict.confidence * 100)}% confidence
            </p>
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="p-6 space-y-4">
        {/* Message */}
        <div>
          <p className="text-lg font-medium text-slate-900">
            {verdict.message}
          </p>
          <p className="text-sm text-slate-600 mt-1">
            {verdict.recommendation}
          </p>
        </div>
        
        {/* Issue Summary */}
        <div className="flex items-center gap-4 flex-wrap">
          {verdict.issueSummary.critical > 0 && (
            <div className="flex items-center gap-1 text-red-600">
              <XCircle className="h-4 w-4" />
              <span className="font-semibold">{verdict.issueSummary.critical}</span>
              <span className="text-sm">critical</span>
            </div>
          )}
          {verdict.issueSummary.major > 0 && (
            <div className="flex items-center gap-1 text-orange-600">
              <AlertTriangle className="h-4 w-4" />
              <span className="font-semibold">{verdict.issueSummary.major}</span>
              <span className="text-sm">major</span>
            </div>
          )}
          {verdict.issueSummary.minor > 0 && (
            <div className="flex items-center gap-1 text-yellow-600">
              <AlertTriangle className="h-4 w-4" />
              <span className="font-semibold">{verdict.issueSummary.minor}</span>
              <span className="text-sm">minor</span>
            </div>
          )}
          {verdict.issueSummary.total === 0 && (
            <div className="flex items-center gap-1 text-green-600">
              <CheckCircle className="h-4 w-4" />
              <span className="font-semibold">No discrepancies</span>
            </div>
          )}
        </div>
        
        {/* Estimated Fee */}
        {verdict.estimatedDiscrepancyFee > 0 && (
          <div className="flex items-center gap-2 p-3 bg-white rounded-lg border">
            <DollarSign className="h-5 w-5 text-slate-400" />
            <div>
              <p className="text-sm text-slate-500">Estimated discrepancy fee</p>
              <p className="font-semibold text-slate-900">
                ${verdict.estimatedDiscrepancyFee.toFixed(0)} USD
              </p>
            </div>
          </div>
        )}
        
        {/* Action Items */}
        {verdict.actionItems.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-700">Priority Actions:</p>
            {verdict.actionItems.slice(0, 3).map((item, idx) => (
              <div 
                key={idx}
                className="flex items-start gap-2 p-2 bg-white rounded border text-sm"
              >
                <span className={cn(
                  'px-2 py-0.5 rounded text-xs font-medium',
                  item.priority === 'critical' && 'bg-red-100 text-red-700',
                  item.priority === 'high' && 'bg-orange-100 text-orange-700',
                  item.priority === 'medium' && 'bg-yellow-100 text-yellow-700',
                )}>
                  {item.priority}
                </span>
                <div className="flex-1">
                  <p className="font-medium text-slate-900">{item.issue}</p>
                  <p className="text-slate-600">{item.action}</p>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Submit Button */}
        {verdict.canSubmitToBank && onSubmit && (
          <Button 
            size="lg" 
            className="w-full bg-gradient-to-r from-blue-600 to-blue-700"
            onClick={onSubmit}
          >
            Submit to Bank
            <ArrowRight className="h-5 w-5 ml-2" />
          </Button>
        )}
        
        {verdict.willBeRejected && (
          <div className="p-3 bg-red-100 rounded-lg text-center">
            <p className="text-sm text-red-800 font-medium">
              Documents will be rejected in current state.
              Please resolve critical issues before submission.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default VerdictBannerV2;

