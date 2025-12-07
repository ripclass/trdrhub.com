/**
 * BankProfileBadge Component
 * 
 * Displays the issuing bank's profile with strictness level and detailed rules.
 */

import { useState } from "react";
import { Building2, ChevronDown, ChevronUp, Info, CheckCircle, XCircle, AlertTriangle, Scale, Calendar, FileText, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

export interface BankProfile {
  bank_code: string;
  bank_name: string;
  strictness: "lenient" | "standard" | "strict";
  document_preferences?: string[];
  tolerance_level?: number;
  // Extended profile data from backend
  port_rules?: {
    strict_spelling?: boolean;
    accept_unlisted_ports?: boolean;
  };
  date_rules?: {
    strict_format?: boolean;
    allow_partial_dates?: boolean;
  };
  amount_rules?: {
    default_tolerance_pct?: number;
  };
  party_rules?: {
    strict_matching?: boolean;
    minimum_similarity?: number;
  };
  special_requirements?: string[];
}

const strictnessColors = {
  lenient: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
  standard: "bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-500/30",
  strict: "bg-orange-500/20 text-orange-700 dark:text-orange-400 border-orange-500/30",
};

const strictnessLabels = {
  lenient: "Lenient",
  standard: "Standard",
  strict: "Strict",
};

const strictnessDescriptions = {
  lenient: "This bank has relaxed validation policies. Minor discrepancies may be accepted.",
  standard: "This bank follows standard UCP600/ISBP745 interpretation. Normal validation applies.",
  strict: "This bank has stringent validation policies. Extra care required with document details.",
};

interface RuleItemProps {
  label: string;
  value: boolean | number | string | undefined;
  positiveLabel?: string;
  negativeLabel?: string;
  icon?: React.ReactNode;
}

function RuleItem({ label, value, positiveLabel = "Yes", negativeLabel = "No", icon }: RuleItemProps) {
  if (value === undefined) return null;
  
  const isPositive = typeof value === "boolean" ? value : typeof value === "number" ? value >= 0.7 : true;
  
  return (
    <div className="flex items-center justify-between py-1.5">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <Badge variant="outline" className={cn(
        "text-[10px] px-1.5",
        isPositive 
          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
          : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
      )}>
        {typeof value === "boolean" 
          ? (value ? positiveLabel : negativeLabel)
          : typeof value === "number"
            ? `${Math.round(value * 100)}%`
            : value}
      </Badge>
    </div>
  );
}

interface BankProfileBadgeProps {
  profile: BankProfile;
}

export function BankProfileBadge({ profile }: BankProfileBadgeProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const hasDetailedRules = profile.port_rules || profile.date_rules || profile.amount_rules || profile.party_rules || profile.special_requirements?.length;
  
  return (
    <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
      <div className={cn(
        "rounded-lg border transition-all duration-200",
        strictnessColors[profile.strictness],
        isExpanded && "shadow-md"
      )}>
        <CollapsibleTrigger asChild>
          <button className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium hover:opacity-90">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              <span className="font-semibold">{profile.bank_name}</span>
              <span className="opacity-60">•</span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="flex items-center gap-1 cursor-help">
                      {strictnessLabels[profile.strictness]}
                      <Info className="w-3 h-3 opacity-60" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    <p className="text-xs">{strictnessDescriptions[profile.strictness]}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            {hasDetailedRules && (
              <div className="flex items-center gap-1 text-xs opacity-60">
                <span>{isExpanded ? "Less" : "Details"}</span>
                {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </div>
            )}
          </button>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <div className="px-3 pb-3 pt-1 border-t border-current/10 space-y-3">
            {/* Port Rules */}
            {profile.port_rules && (
              <div className="space-y-1">
                <div className="text-[10px] font-semibold uppercase tracking-wider opacity-60">Port Matching</div>
                <RuleItem 
                  label="Strict Spelling Required" 
                  value={profile.port_rules.strict_spelling} 
                  positiveLabel="Strict"
                  negativeLabel="Flexible"
                  icon={<FileText className="w-3 h-3" />}
                />
                <RuleItem 
                  label="Accept Unlisted Ports" 
                  value={profile.port_rules.accept_unlisted_ports}
                  icon={<CheckCircle className="w-3 h-3" />}
                />
              </div>
            )}
            
            {/* Date Rules */}
            {profile.date_rules && (
              <div className="space-y-1">
                <div className="text-[10px] font-semibold uppercase tracking-wider opacity-60">Date Handling</div>
                <RuleItem 
                  label="Strict Format Required" 
                  value={profile.date_rules.strict_format}
                  positiveLabel="Strict"
                  negativeLabel="Flexible"
                  icon={<Calendar className="w-3 h-3" />}
                />
                <RuleItem 
                  label="Partial Dates Allowed" 
                  value={profile.date_rules.allow_partial_dates}
                  icon={<CheckCircle className="w-3 h-3" />}
                />
              </div>
            )}
            
            {/* Amount Rules */}
            {profile.amount_rules && (
              <div className="space-y-1">
                <div className="text-[10px] font-semibold uppercase tracking-wider opacity-60">Amount Tolerance</div>
                <RuleItem 
                  label="Default Tolerance" 
                  value={profile.amount_rules.default_tolerance_pct !== undefined 
                    ? `±${profile.amount_rules.default_tolerance_pct}%` 
                    : undefined}
                  icon={<Scale className="w-3 h-3" />}
                />
              </div>
            )}
            
            {/* Party Name Rules */}
            {profile.party_rules && (
              <div className="space-y-1">
                <div className="text-[10px] font-semibold uppercase tracking-wider opacity-60">Party Name Matching</div>
                <RuleItem 
                  label="Strict Name Match" 
                  value={profile.party_rules.strict_matching}
                  positiveLabel="Strict"
                  negativeLabel="Fuzzy OK"
                  icon={<Users className="w-3 h-3" />}
                />
                {profile.party_rules.minimum_similarity !== undefined && (
                  <RuleItem 
                    label="Min. Similarity Required" 
                    value={profile.party_rules.minimum_similarity}
                    icon={<AlertTriangle className="w-3 h-3" />}
                  />
                )}
              </div>
            )}
            
            {/* Special Requirements */}
            {profile.special_requirements && profile.special_requirements.length > 0 && (
              <div className="space-y-1">
                <div className="text-[10px] font-semibold uppercase tracking-wider opacity-60">Special Notes</div>
                <ul className="text-xs space-y-1">
                  {profile.special_requirements.map((req, idx) => (
                    <li key={idx} className="flex items-start gap-1.5 text-muted-foreground">
                      <AlertTriangle className="w-3 h-3 mt-0.5 text-amber-500 flex-shrink-0" />
                      {req}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* UCP600 Reference */}
            <div className="pt-2 border-t border-current/10">
              <p className="text-[10px] text-muted-foreground">
                Bank profiles affect how UCP600/ISBP745 rules are interpreted during validation.
              </p>
            </div>
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

