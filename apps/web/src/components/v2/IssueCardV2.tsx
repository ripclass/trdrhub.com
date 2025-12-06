/**
 * V2 Issue Card with Citations
 * 
 * Key differentiator: EVERY issue shows UCP600/ISBP745 citations.
 * This is what makes LCopilot bank-grade.
 */

import { useState } from 'react';
import { 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  XCircle,
  ChevronDown,
  ChevronUp,
  FileText,
  BookOpen,
  Wrench,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export interface Citations {
  ucp600?: string[];
  isbp745?: string[];
  urc522?: string[];
  urr725?: string[];
  swift?: string[];
}

export interface IssueV2 {
  id: string;
  ruleId: string;
  title: string;
  severity: 'critical' | 'major' | 'minor' | 'info';
  citations: Citations;
  bankMessage: string;
  explanation: string;
  expected: string;
  found: string;
  suggestion: string;
  documents: string[];
  canAmend: boolean;
  amendmentCost?: number;
  confidence: number;
}

interface IssueCardV2Props {
  issue: IssueV2;
  onAmendClick?: (issue: IssueV2) => void;
}

const severityConfig = {
  critical: {
    icon: XCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    badgeVariant: 'destructive' as const,
    label: 'CRITICAL',
  },
  major: {
    icon: AlertTriangle,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    badgeVariant: 'warning' as const,
    label: 'MAJOR',
  },
  minor: {
    icon: AlertCircle,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    badgeVariant: 'secondary' as const,
    label: 'MINOR',
  },
  info: {
    icon: Info,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    badgeVariant: 'outline' as const,
    label: 'INFO',
  },
};

// UCP600 article descriptions for tooltips
const UCP600_DESCRIPTIONS: Record<string, string> = {
  '14': 'Standard for Examination of Documents',
  '14(a)': 'Banks must examine presentation to determine compliance on face',
  '14(b)': 'Bank has maximum 5 banking days for examination',
  '14(c)': 'Data in documents must not conflict',
  '14(d)': 'Data need not be identical but must not conflict',
  '18': 'Commercial Invoice',
  '18(a)': 'Invoice must appear to be issued by beneficiary',
  '18(b)': 'Invoice must be made out in name of applicant',
  '18(c)': 'Description of goods must correspond with LC',
  '20': 'Bill of Lading',
  '20(a)': 'B/L requirements (carrier name, signature, dates)',
  '27': 'Clean Transport Document',
  '28': 'Insurance Document and Coverage',
  '29': 'Extension of Expiry Date or Period for Presentation',
  '30': 'Tolerance in Credit Amount, Quantity and Unit Prices',
};

export function IssueCardV2({ issue, onAmendClick }: IssueCardV2Props) {
  const [expanded, setExpanded] = useState(false);
  const config = severityConfig[issue.severity];
  const Icon = config.icon;
  
  const hasCitations = 
    (issue.citations.ucp600?.length ?? 0) > 0 ||
    (issue.citations.isbp745?.length ?? 0) > 0;
  
  return (
    <Card className={cn(
      'transition-all duration-200',
      config.borderColor,
      expanded && 'ring-2 ring-offset-2',
      issue.severity === 'critical' && 'ring-red-500',
      issue.severity === 'major' && 'ring-orange-500',
    )}>
      <CardHeader 
        className={cn('pb-2 cursor-pointer', config.bgColor)}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <Icon className={cn('h-5 w-5 mt-0.5 flex-shrink-0', config.color)} />
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant={config.badgeVariant} className="text-xs">
                  {config.label}
                </Badge>
                {hasCitations && (
                  <Badge variant="outline" className="text-xs bg-white">
                    <BookOpen className="h-3 w-3 mr-1" />
                    UCP600 Cited
                  </Badge>
                )}
              </div>
              <h3 className="font-semibold text-slate-900 leading-tight">
                {issue.title}
              </h3>
              {!expanded && (
                <p className="text-sm text-slate-600 line-clamp-2">
                  {issue.explanation}
                </p>
              )}
            </div>
          </div>
          
          <Button variant="ghost" size="sm" className="flex-shrink-0">
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardHeader>
      
      {expanded && (
        <CardContent className="pt-4 space-y-4">
          {/* Bank Message - Formatted for examiner */}
          <div className="p-3 bg-slate-100 rounded-lg border">
            <p className="text-sm font-medium text-slate-700">
              Bank Examiner Message:
            </p>
            <p className="text-sm text-slate-900 mt-1 font-mono">
              {issue.bankMessage}
            </p>
          </div>
          
          {/* Citations - THE KEY DIFFERENTIATOR */}
          {hasCitations && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-700 flex items-center gap-1">
                <BookOpen className="h-4 w-4" />
                Regulatory Citations
              </p>
              <div className="flex flex-wrap gap-2">
                <TooltipProvider>
                  {issue.citations.ucp600?.map((art) => (
                    <Tooltip key={art}>
                      <TooltipTrigger asChild>
                        <Badge 
                          variant="secondary" 
                          className="cursor-help bg-blue-100 text-blue-800 hover:bg-blue-200"
                        >
                          UCP600 Art. {art}
                        </Badge>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p className="font-medium">Article {art}</p>
                        <p className="text-xs text-slate-400">
                          {UCP600_DESCRIPTIONS[art] || 'ICC Uniform Customs and Practice for Documentary Credits'}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  ))}
                  {issue.citations.isbp745?.map((para) => (
                    <Tooltip key={para}>
                      <TooltipTrigger asChild>
                        <Badge 
                          variant="secondary"
                          className="cursor-help bg-purple-100 text-purple-800 hover:bg-purple-200"
                        >
                          ISBP745 ¶{para}
                        </Badge>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="font-medium">Paragraph {para}</p>
                        <p className="text-xs text-slate-400">
                          ICC International Standard Banking Practice
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  ))}
                  {issue.citations.swift?.map((field) => (
                    <Badge 
                      key={field}
                      variant="outline"
                      className="bg-slate-100"
                    >
                      SWIFT {field}
                    </Badge>
                  ))}
                </TooltipProvider>
              </div>
            </div>
          )}
          
          {/* Expected vs Found */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-green-50 rounded-lg border border-green-200">
              <p className="text-xs font-medium text-green-700 uppercase tracking-wide">
                Expected
              </p>
              <p className="text-sm text-green-900 mt-1">
                {issue.expected}
              </p>
            </div>
            <div className="p-3 bg-red-50 rounded-lg border border-red-200">
              <p className="text-xs font-medium text-red-700 uppercase tracking-wide">
                Found
              </p>
              <p className="text-sm text-red-900 mt-1">
                {issue.found}
              </p>
            </div>
          </div>
          
          {/* Suggestion */}
          <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
            <p className="text-xs font-medium text-amber-700 uppercase tracking-wide flex items-center gap-1">
              <Wrench className="h-3 w-3" />
              Suggested Fix
            </p>
            <p className="text-sm text-amber-900 mt-1">
              {issue.suggestion}
            </p>
          </div>
          
          {/* Source Documents */}
          {issue.documents.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <FileText className="h-4 w-4 text-slate-400" />
              <span className="text-xs text-slate-500">Affects:</span>
              {issue.documents.map((doc) => (
                <Badge key={doc} variant="outline" className="text-xs">
                  {doc}
                </Badge>
              ))}
            </div>
          )}
          
          {/* Amendment Button */}
          {issue.canAmend && onAmendClick && (
            <div className="pt-2 border-t">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => onAmendClick(issue)}
                className="w-full"
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Generate Amendment
                {issue.amendmentCost && (
                  <span className="ml-2 text-slate-500">
                    (~${issue.amendmentCost})
                  </span>
                )}
              </Button>
            </div>
          )}
          
          {/* Debug: Rule ID */}
          <p className="text-xs text-slate-400 pt-2 border-t">
            Rule: {issue.ruleId}
          </p>
        </CardContent>
      )}
    </Card>
  );
}

export default IssueCardV2;

