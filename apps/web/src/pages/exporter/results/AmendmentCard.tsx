/**
 * AmendmentCard Component
 * 
 * Displays available amendments for LC discrepancies with download options.
 */

import { useMemo, useState } from "react";
import { FileCheck, Download, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

// Amendment Types
export interface AmendmentFieldChange {
  tag: string;
  name: string;
  current: string;
  proposed: string;
}

export interface Amendment {
  issue_id: string;
  field: AmendmentFieldChange;
  narrative: string;
  mt707_text: string;
  iso20022_xml?: string;
  bank_processing_days: number;
  estimated_fee_usd: number;
}

export interface AmendmentsAvailable {
  count: number;
  amendments: Amendment[];
  total_estimated_fee_usd: number;
  total_processing_days: number;
}

interface AmendmentCardProps {
  amendments: AmendmentsAvailable;
  onDownloadMT707: (amendment: Amendment) => void;
  onDownloadISO20022: (amendment: Amendment) => void;
}

export function AmendmentCard({ 
  amendments, 
  onDownloadMT707,
  onDownloadISO20022,
}: AmendmentCardProps) {
  const [expanded, setExpanded] = useState(false);

  const amendmentKeys = useMemo(
    () => amendments.amendments.map((amendment, idx) => amendment.issue_id || `${amendment.field.tag}-${idx}`),
    [amendments.amendments],
  );

  const [selectedFormats, setSelectedFormats] = useState<Record<string, "MT707" | "ISO20022">>({});

  const getSelectedFormat = (key: string, hasIso: boolean): "MT707" | "ISO20022" => {
    const selected = selectedFormats[key];
    if (selected === "ISO20022" && !hasIso) return "MT707";
    return selected ?? "MT707";
  };

  if (amendments.count === 0) return null;

  return (
    <Card className="mt-4 bg-blue-500/5 border-blue-500/20">
      <CardContent className="pt-4 pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <FileCheck className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="font-medium text-sm text-blue-400">
                {amendments.count} Amendment{amendments.count > 1 ? "s" : ""} Available
              </p>
              <p className="text-xs text-muted-foreground">
                Some discrepancies can be fixed via LC amendment • Est. fee: USD {amendments.total_estimated_fee_usd.toFixed(2)}
              </p>
            </div>
          </div>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="text-blue-400 border-blue-500/30 hover:bg-blue-500/10"
          >
            {expanded ? "Hide" : "View"} Amendments
          </Button>
        </div>
        
        {expanded && (
          <div className="mt-4 pt-4 border-t border-blue-500/20 space-y-3">
            {amendments.amendments.map((amendment, idx) => {
              const key = amendmentKeys[idx] ?? `${amendment.field.tag}-${idx}`;
              const hasIso = Boolean(amendment.iso20022_xml);
              const selectedFormat = getSelectedFormat(key, hasIso);

              return (
                <div key={key} className="flex items-start justify-between p-3 rounded-lg bg-background/50 gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">
                      Field {amendment.field.tag}: {amendment.field.name}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {amendment.field.current} → {amendment.field.proposed}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {amendment.narrative} • ~{amendment.bank_processing_days} days • USD {amendment.estimated_fee_usd}
                    </p>
                    <p className="text-[11px] mt-2 text-muted-foreground">
                      Selected format for this amendment: <span className="font-semibold text-foreground">{selectedFormat}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant={selectedFormat === "MT707" ? "default" : "outline"}
                      size="sm"
                      onClick={() => {
                        setSelectedFormats((prev) => ({ ...prev, [key]: "MT707" }));
                        onDownloadMT707(amendment);
                      }}
                      className={selectedFormat === "MT707" ? "bg-blue-600 text-white hover:bg-blue-500" : "text-blue-400 border-blue-500/40 hover:bg-blue-500/10"}
                      title="Download legacy SWIFT MT707 format"
                    >
                      <Download className="w-4 h-4 mr-1" />
                      MT707
                    </Button>
                    {hasIso && (
                      <Button
                        variant={selectedFormat === "ISO20022" ? "default" : "outline"}
                        size="sm"
                        onClick={() => {
                          setSelectedFormats((prev) => ({ ...prev, [key]: "ISO20022" }));
                          onDownloadISO20022(amendment);
                        }}
                        className={selectedFormat === "ISO20022" ? "bg-emerald-600 text-white hover:bg-emerald-500" : "text-emerald-400 border-emerald-500/40 hover:bg-emerald-500/10"}
                        title="Download ISO20022 XML format (modern standard)"
                      >
                        <Download className="w-4 h-4 mr-1" />
                        ISO20022
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
            <p className="text-xs text-muted-foreground pt-2 border-t border-blue-500/10">
              <span className="font-medium">Format selection is per amendment card.</span>
              <span className="ml-2"><span className="font-medium">MT707:</span> Legacy SWIFT FIN format</span>
              <span className="ml-2"><span className="font-medium">ISO20022:</span> Modern XML standard (trad.002)</span>
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Tolerance Badge Component (for issue cards)
export interface ToleranceApplied {
  tolerance_percent: number;
  source: string;
  explicit: boolean;
}

export function ToleranceBadge({ tolerance }: { tolerance: ToleranceApplied }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400 border border-green-500/30">
      <CheckCircle className="w-3 h-3" />
      ±{tolerance.tolerance_percent}% tolerance ({tolerance.source.replace(/_/g, ' ')})
    </span>
  );
}

