/**
 * BankProfileBadge Component
 * 
 * Displays the issuing bank's profile with strictness level.
 */

import { Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface BankProfile {
  bank_code: string;
  bank_name: string;
  strictness: "lenient" | "standard" | "strict";
  document_preferences: string[];
  tolerance_level: number;
}

const strictnessColors = {
  lenient: "bg-green-500/20 text-green-400 border-green-500/30",
  standard: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  strict: "bg-orange-500/20 text-orange-400 border-orange-500/30",
};

const strictnessLabels = {
  lenient: "Lenient",
  standard: "Standard",
  strict: "Strict",
};

interface BankProfileBadgeProps {
  profile: BankProfile;
}

export function BankProfileBadge({ profile }: BankProfileBadgeProps) {
  return (
    <div className={cn(
      "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium",
      strictnessColors[profile.strictness]
    )}>
      <Building2 className="w-3.5 h-3.5" />
      <span>{profile.bank_name}</span>
      <span className="opacity-60">•</span>
      <span>{strictnessLabels[profile.strictness]}</span>
    </div>
  );
}

