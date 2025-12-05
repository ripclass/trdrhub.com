/**
 * LC Expiry Warning Component
 * 
 * Shows warning when shipment ETA approaches or exceeds LC expiry date.
 */

import { AlertTriangle, Clock, FileText, AlertCircle, CheckCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

interface LCExpiryWarningProps {
  eta?: string | Date;
  lcExpiry?: string | Date;
  lcNumber?: string;
  containerNumber?: string;
  className?: string;
}

export default function LCExpiryWarning({
  eta,
  lcExpiry,
  lcNumber,
  containerNumber,
  className = "",
}: LCExpiryWarningProps) {
  if (!eta || !lcExpiry) return null;

  const etaDate = new Date(eta);
  const expiryDate = new Date(lcExpiry);
  const now = new Date();
  
  const daysUntilEta = Math.ceil((etaDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  const daysUntilExpiry = Math.ceil((expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  const daysAfterEta = Math.ceil((expiryDate.getTime() - etaDate.getTime()) / (1000 * 60 * 60 * 24));

  // Determine risk level
  type RiskLevel = "critical" | "high" | "medium" | "safe";
  let riskLevel: RiskLevel = "safe";
  let message = "";
  let description = "";

  if (etaDate > expiryDate) {
    // ETA is AFTER LC expiry - CRITICAL
    riskLevel = "critical";
    message = "LC Will Expire Before Arrival";
    description = `ETA is ${Math.abs(daysAfterEta)} days after LC expiry. Documents cannot be negotiated.`;
  } else if (daysAfterEta <= 3) {
    // Less than 3 days between ETA and LC expiry
    riskLevel = "high";
    message = "Critical LC Timing Risk";
    description = `Only ${daysAfterEta} day${daysAfterEta !== 1 ? 's' : ''} between arrival and LC expiry. Document presentation at risk.`;
  } else if (daysAfterEta <= 7) {
    // 3-7 days between ETA and LC expiry
    riskLevel = "medium";
    message = "LC Timing Warning";
    description = `${daysAfterEta} days between arrival and LC expiry. Monitor closely and prepare documents.`;
  } else if (daysAfterEta <= 14) {
    // 7-14 days - low risk warning
    riskLevel = "safe";
    message = "LC Timeline OK";
    description = `${daysAfterEta} days between arrival and LC expiry. Sufficient time for document presentation.`;
  } else {
    // More than 14 days - all good
    return null; // Don't show anything if timing is fine
  }

  const getColors = () => {
    switch (riskLevel) {
      case "critical":
        return {
          bg: "bg-red-500/10",
          border: "border-red-500/30",
          icon: "text-red-500",
          badge: "bg-red-500/20 text-red-500 border-red-500/30",
        };
      case "high":
        return {
          bg: "bg-amber-500/10",
          border: "border-amber-500/30",
          icon: "text-amber-500",
          badge: "bg-amber-500/20 text-amber-500 border-amber-500/30",
        };
      case "medium":
        return {
          bg: "bg-yellow-500/10",
          border: "border-yellow-500/30",
          icon: "text-yellow-500",
          badge: "bg-yellow-500/20 text-yellow-500 border-yellow-500/30",
        };
      default:
        return {
          bg: "bg-emerald-500/10",
          border: "border-emerald-500/30",
          icon: "text-emerald-500",
          badge: "bg-emerald-500/20 text-emerald-500 border-emerald-500/30",
        };
    }
  };

  const colors = getColors();
  const Icon = riskLevel === "critical" || riskLevel === "high" ? AlertTriangle : 
               riskLevel === "medium" ? AlertCircle : CheckCircle;

  return (
    <Card className={`${colors.bg} ${colors.border} border ${className}`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          <div className={`mt-0.5 ${colors.icon}`}>
            <Icon className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-semibold">{message}</h4>
              <Badge className={colors.badge}>
                {riskLevel === "critical" ? "CRITICAL" : 
                 riskLevel === "high" ? "HIGH RISK" : 
                 riskLevel === "medium" ? "WARNING" : "OK"}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-3">
              {description}
            </p>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">ETA</p>
                <p className="font-medium">{etaDate.toLocaleDateString()}</p>
                <p className="text-xs text-muted-foreground">
                  {daysUntilEta > 0 ? `in ${daysUntilEta} days` : "Arrived"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">LC Expiry</p>
                <p className="font-medium">{expiryDate.toLocaleDateString()}</p>
                <p className="text-xs text-muted-foreground">
                  {daysUntilExpiry > 0 ? `in ${daysUntilExpiry} days` : "EXPIRED"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Buffer Time</p>
                <p className={`font-medium ${daysAfterEta <= 3 ? "text-red-500" : daysAfterEta <= 7 ? "text-amber-500" : "text-emerald-500"}`}>
                  {daysAfterEta} days
                </p>
              </div>
              {lcNumber && (
                <div>
                  <p className="text-muted-foreground text-xs">LC Number</p>
                  <p className="font-mono font-medium">{lcNumber}</p>
                </div>
              )}
            </div>

            {(riskLevel === "critical" || riskLevel === "high") && (
              <div className="mt-4 pt-3 border-t border-dashed flex flex-wrap gap-2">
                <Button size="sm" variant="outline" asChild>
                  <Link to="/hub">
                    <FileText className="w-4 h-4 mr-1" />
                    View LC in LCopilot
                  </Link>
                </Button>
                <Button size="sm" variant="outline">
                  <Clock className="w-4 h-4 mr-1" />
                  Request LC Extension
                </Button>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

