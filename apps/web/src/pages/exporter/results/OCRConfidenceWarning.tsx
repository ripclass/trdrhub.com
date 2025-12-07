/**
 * OCRConfidenceWarning Component
 * 
 * Displays a warning banner when OCR extraction confidence is low.
 */

import { AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface ExtractionConfidence {
  average_confidence: number;
  lowest_confidence_document: string | null;
  lowest_confidence_value: number;
  recommendations: string[];
}

interface OCRConfidenceWarningProps {
  confidence: ExtractionConfidence;
}

export function OCRConfidenceWarning({ confidence }: OCRConfidenceWarningProps) {
  if (confidence.average_confidence >= 0.7) return null;
  
  const isLow = confidence.average_confidence < 0.5;
  
  return (
    <Card className={cn(
      "border-2 mt-4",
      isLow 
        ? "bg-red-500/10 border-red-500/30" 
        : "bg-yellow-500/10 border-yellow-500/30"
    )}>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className={cn(
            "w-5 h-5 mt-0.5",
            isLow ? "text-red-400" : "text-yellow-400"
          )} />
          <div className="flex-1">
            <p className={cn(
              "font-medium text-sm",
              isLow ? "text-red-400" : "text-yellow-400"
            )}>
              {isLow ? "Low OCR Extraction Quality" : "OCR Quality Warning"}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Average extraction confidence: <span className="font-semibold">{(confidence.average_confidence * 100).toFixed(0)}%</span>
              {confidence.lowest_confidence_document && (
                <> • Lowest: <span className="font-medium">{confidence.lowest_confidence_document}</span> ({(confidence.lowest_confidence_value * 100).toFixed(0)}%)</>
              )}
            </p>
            {confidence.recommendations.length > 0 && (
              <ul className="mt-2 space-y-1">
                {confidence.recommendations.map((rec, idx) => (
                  <li key={idx} className="text-xs text-muted-foreground flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-current" />
                    {rec}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

