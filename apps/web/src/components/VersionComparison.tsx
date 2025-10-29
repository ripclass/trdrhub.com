import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { useCompare, type LCVersion, type VersionComparison } from "@/hooks/use-versions";
import { useToast } from "@/hooks/use-toast";
import {
  GitBranch,
  TrendingUp,
  TrendingDown,
  Minus,
  Plus,
  AlertTriangle,
  CheckCircle,
  XCircle
} from "lucide-react";

interface VersionComparisonProps {
  lcNumber: string;
  versions: LCVersion[];
  currentVersion: string;
}

export function VersionComparisonDialog({ lcNumber, versions, currentVersion }: VersionComparisonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [fromVersion, setFromVersion] = useState("");
  const [comparison, setComparison] = useState<VersionComparison | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { compareVersions } = useCompare();
  const { toast } = useToast();

  const handleCompare = async () => {
    if (!fromVersion || fromVersion === currentVersion) {
      toast({
        title: "Invalid Selection",
        description: "Please select a different version to compare with.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const result = await compareVersions(lcNumber, fromVersion, currentVersion);
      setComparison(result);
    } catch (error) {
      console.error('Failed to compare versions:', error);
      toast({
        title: "Comparison Failed",
        description: "Could not compare versions. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high':
      case 'critical':
        return <XCircle className="w-4 h-4 text-destructive" />;
      case 'medium':
        return <AlertTriangle className="w-4 h-4 text-warning" />;
      case 'low':
      case 'minor':
        return <CheckCircle className="w-4 h-4 text-success" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getImprovementText = (score: number) => {
    if (score > 0.3) return { text: "Significant Improvement", color: "text-green-600", icon: TrendingUp };
    if (score > 0) return { text: "Minor Improvement", color: "text-green-500", icon: TrendingUp };
    if (score < -0.3) return { text: "Needs Attention", color: "text-red-600", icon: TrendingDown };
    if (score < 0) return { text: "Minor Issues", color: "text-red-500", icon: TrendingDown };
    return { text: "No Change", color: "text-gray-500", icon: Minus };
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" disabled={versions.length < 2}>
          <GitBranch className="w-4 h-4 mr-2" />
          Compare Versions
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Version Comparison - LC #{lcNumber}</DialogTitle>
          <DialogDescription>
            Compare discrepancies and validation results between different versions
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Version Selection */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Compare:</span>
              <Select value={fromVersion} onValueChange={setFromVersion}>
                <SelectTrigger className="w-24">
                  <SelectValue placeholder="From" />
                </SelectTrigger>
                <SelectContent>
                  {versions
                    .filter(v => v.version !== currentVersion)
                    .map((version) => (
                      <SelectItem key={version.version} value={version.version}>
                        {version.version}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            <span className="text-muted-foreground">→</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">To:</span>
              <Badge variant="outline">{currentVersion}</Badge>
            </div>
            <Button onClick={handleCompare} disabled={!fromVersion || isLoading}>
              {isLoading ? "Comparing..." : "Compare"}
            </Button>
          </div>

          {/* Comparison Results */}
          {comparison && (
            <div className="space-y-6">
              {/* Summary */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-foreground">
                        {comparison.summary.total_changes}
                      </div>
                      <div className="text-sm text-muted-foreground">Total Changes</div>
                    </div>
                    <div className="text-center">
                      <div className="flex items-center justify-center gap-2">
                        {(() => {
                          const improvement = getImprovementText(comparison.summary.improvement_score);
                          const Icon = improvement.icon;
                          return (
                            <>
                              <Icon className={`w-5 h-5 ${improvement.color}`} />
                              <span className={`text-sm font-medium ${improvement.color}`}>
                                {improvement.text}
                              </span>
                            </>
                          );
                        })()}
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-foreground">
                        {((1 + comparison.summary.improvement_score) * 50).toFixed(0)}%
                      </div>
                      <div className="text-sm text-muted-foreground">Quality Score</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Changes Detail */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Removed Discrepancies */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2 text-green-600">
                      <Minus className="w-4 h-4" />
                      Resolved ({comparison.changes.removed_discrepancies.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {comparison.changes.removed_discrepancies.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No discrepancies resolved</p>
                    ) : (
                      <div className="space-y-2">
                        {comparison.changes.removed_discrepancies.map((disc: any, index: number) => (
                          <div key={index} className="flex items-start gap-2 text-sm">
                            {getSeverityIcon(disc.severity)}
                            <div>
                              <div className="font-medium">{disc.title}</div>
                              <div className="text-muted-foreground text-xs">{disc.description}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Added Discrepancies */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2 text-red-600">
                      <Plus className="w-4 h-4" />
                      New Issues ({comparison.changes.added_discrepancies.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {comparison.changes.added_discrepancies.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No new discrepancies</p>
                    ) : (
                      <div className="space-y-2">
                        {comparison.changes.added_discrepancies.map((disc: any, index: number) => (
                          <div key={index} className="flex items-start gap-2 text-sm">
                            {getSeverityIcon(disc.severity)}
                            <div>
                              <div className="font-medium">{disc.title}</div>
                              <div className="text-muted-foreground text-xs">{disc.description}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Modified Discrepancies */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2 text-blue-600">
                      <GitBranch className="w-4 h-4" />
                      Modified ({comparison.changes.modified_discrepancies.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {comparison.changes.modified_discrepancies.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No modified discrepancies</p>
                    ) : (
                      <div className="space-y-2">
                        {comparison.changes.modified_discrepancies.map((disc: any, index: number) => (
                          <div key={index} className="flex items-start gap-2 text-sm">
                            {getSeverityIcon(disc.severity)}
                            <div>
                              <div className="font-medium">{disc.title}</div>
                              <div className="text-muted-foreground text-xs">{disc.description}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}