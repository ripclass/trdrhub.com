/**
 * AmendmentCard Component
 * 
 * Displays available amendments for LC discrepancies with download options.
 */

import { useState } from "react";
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
            {amendments.amendments.map((amendment, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-background/50">
                <div className="flex-1">
                  <p className="text-sm font-medium">
                    Field {amendment.field.tag}: {amendment.field.name}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {amendment.field.current} → {amendment.field.proposed}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {amendment.narrative} • ~{amendment.bank_processing_days} days • USD {amendment.estimated_fee_usd}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDownloadMT707(amendment)}
                    className="text-blue-400 hover:text-blue-300"
                    title="Download legacy SWIFT MT707 format"
                  >
                    <Download className="w-4 h-4 mr-1" />
                    MT707
                  </Button>
                  {amendment.iso20022_xml && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDownloadISO20022(amendment)}
                      className="text-emerald-400 hover:text-emerald-300"
                      title="Download ISO20022 XML format (modern standard)"
                    >
                      <Download className="w-4 h-4 mr-1" />
                      ISO20022
                    </Button>
                  )}
                </div>
              </div>
            ))}
            <p className="text-xs text-muted-foreground pt-2 border-t border-blue-500/10">
              <span className="font-medium">MT707:</span> Legacy SWIFT FIN format • 
              <span className="font-medium ml-2">ISO20022:</span> Modern XML standard (trad.002)
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

