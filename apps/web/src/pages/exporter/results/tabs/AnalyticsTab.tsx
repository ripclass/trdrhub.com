/**
 * Analytics Tab Component
 * Shows processing performance and document analytics
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { BarChart3, PieChart, TrendingUp, Sparkles } from "lucide-react";
import { safeString } from "../utils";

const StatusBadge = ({ 
  status, 
  children 
}: { 
  status: 'success' | 'warning' | 'error' | string; 
  children: React.ReactNode;
}) => {
  const variants: Record<string, string> = {
    success: "bg-success/10 text-success border-success/20",
    warning: "bg-warning/10 text-warning border-warning/20",
    error: "bg-destructive/10 text-destructive border-destructive/20",
  };
  return (
    <Badge variant="outline" className={variants[status] || variants.success}>
      {children}
    </Badge>
  );
};

interface DocumentProcessingItem {
  name?: string;
  type?: string;
  issues?: number;
  status?: 'success' | 'warning' | 'error' | string;
  risk?: string;
}

interface AnalyticsTabProps {
  analyticsAvailable: boolean;
  extractionAccuracy: number;
  lcComplianceScore: number;
  customsReadyScore: number;
  processingTime: string;
  totalDocuments: number;
  successCount: number;
  warningCount: number;
  errorCount: number;
  performanceInsights: string[];
  documentProcessingList: DocumentProcessingItem[];
  documents: { type?: string }[];
}

export function AnalyticsTab({
  analyticsAvailable,
  extractionAccuracy,
  lcComplianceScore,
  customsReadyScore,
  processingTime,
  totalDocuments,
  successCount,
  warningCount,
  errorCount,
  performanceInsights,
  documentProcessingList,
  documents,
}: AnalyticsTabProps) {
  if (!analyticsAvailable) {
    return (
      <Card className="border border-dashed border-muted-foreground/40 bg-muted/10">
        <CardContent className="py-10 text-center space-y-2">
          <Sparkles className="w-8 h-8 mx-auto text-muted-foreground" />
          <p className="text-lg font-semibold text-foreground">Analytics unavailable</p>
          <p className="text-sm text-muted-foreground">
            Analytics were not generated for this validation run. Re-run the validation to capture full metrics.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="grid md:grid-cols-2 gap-6">
        <Card className="shadow-soft border border-border/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Processing Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Document Extraction Accuracy</span>
                <span className="text-sm font-medium">{extractionAccuracy}%</span>
              </div>
              <Progress value={extractionAccuracy} className="h-2" />
              <div className="flex items-center justify-between">
                <span className="text-sm">LC Compliance Check</span>
                <span className="text-sm font-medium">{lcComplianceScore}%</span>
              </div>
              <Progress value={lcComplianceScore} className="h-2" />
              <div className="flex items-center justify-between">
                <span className="text-sm">Customs Readiness</span>
                <span className="text-sm font-medium">{customsReadyScore}%</span>
              </div>
              <Progress value={customsReadyScore} className="h-2" />
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <div className="text-center p-3 bg-success/5 border border-success/20 rounded-lg">
                <div className="text-lg font-bold text-success">{processingTime}</div>
                <div className="text-xs text-muted-foreground">Processing Time</div>
              </div>
              <div className="text-center p-3 bg-primary/5 border border-primary/20 rounded-lg">
                <div className="text-lg font-bold text-primary">{totalDocuments}/{totalDocuments}</div>
                <div className="text-xs text-muted-foreground">Documents Processed</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow-soft border border-border/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="w-5 h-5" />
              Document Status Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-success rounded-full"></div>
                  <span className="text-sm">Verified Documents</span>
                </div>
                <span className="text-sm font-medium">
                  {successCount} ({totalDocuments ? Math.round((successCount/totalDocuments)*100) : 0}%)
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-warning rounded-full"></div>
                  <span className="text-sm">Minor Issues</span>
                </div>
                <span className="text-sm font-medium">
                  {warningCount} ({totalDocuments ? Math.round((warningCount/totalDocuments)*100) : 0}%)
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-destructive rounded-full"></div>
                  <span className="text-sm">Critical Issues</span>
                </div>
                <span className="text-sm font-medium">
                  {errorCount} ({totalDocuments ? Math.round((errorCount/totalDocuments)*100) : 0}%)
                </span>
              </div>
            </div>
            <div className="mt-4 p-3 bg-gradient-primary/5 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium text-primary">Performance Insights</span>
              </div>
              <ul className="text-xs text-muted-foreground space-y-1">
                {performanceInsights.map((insight, idx) => (
                  <li key={idx}>- {insight}</li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
      <Card className="shadow-soft border border-border/60">
        <CardHeader>
          <CardTitle>Document Processing Analytics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2">Document</th>
                  <th className="text-left py-2">Issues</th>
                  <th className="text-left py-2">Status</th>
                  <th className="text-left py-2">Risk</th>
                </tr>
              </thead>
              <tbody>
                {documentProcessingList.map((item, index) => (
                  <tr key={item.name ?? index} className="border-b border-gray-200/50">
                    <td className="py-3 font-medium">{safeString(item.type ?? documents[index]?.type)}</td>
                    <td className="py-3 text-muted-foreground">{item.issues ?? 0}</td>
                    <td className="py-3">
                      <StatusBadge status={item.status || 'success'}>
                        {item.status === 'success' ? 'Verified' : item.status === 'warning' ? 'Review' : 'Fix Required'}
                      </StatusBadge>
                    </td>
                    <td className="py-3 text-muted-foreground">{item.risk ?? 'low'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
