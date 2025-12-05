/**
 * Version History Page
 * 
 * View and manage version history of LC applications with diff view.
 */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ArrowLeft,
  History,
  Eye,
  RotateCcw,
  GitCompare,
  Plus,
  Minus,
  RefreshCw,
  Clock,
  User,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface Version {
  id: string;
  version_number: number;
  change_summary: string;
  created_at: string;
  created_by?: string;
}

interface Diff {
  field: string;
  label: string;
  old_value: any;
  new_value: any;
  change_type: "modified" | "added" | "removed";
}

interface DiffResponse {
  version: {
    id: string;
    version_number: number;
    created_at: string;
  };
  compare_to: {
    id: string;
    version_number: number;
  } | null;
  diffs: Diff[];
  change_count: number;
}

export default function VersionHistoryPage() {
  const { applicationId } = useParams();
  const navigate = useNavigate();
  const { session } = useAuth();
  const { toast } = useToast();

  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(true);
  const [refNumber, setRefNumber] = useState<string>("");
  
  const [selectedVersion, setSelectedVersion] = useState<Version | null>(null);
  const [diffData, setDiffData] = useState<DiffResponse | null>(null);
  const [loadingDiff, setLoadingDiff] = useState(false);
  const [showDiffDialog, setShowDiffDialog] = useState(false);
  
  const [restoreVersion, setRestoreVersion] = useState<Version | null>(null);
  const [restoring, setRestoring] = useState(false);
  
  const [creatingVersion, setCreatingVersion] = useState(false);

  useEffect(() => {
    if (applicationId && session?.access_token) {
      fetchVersions();
    }
  }, [applicationId, session?.access_token]);

  const fetchVersions = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/lc-builder/applications/${applicationId}/versions`,
        {
          headers: {
            Authorization: `Bearer ${session?.access_token}`,
          },
        }
      );

      if (res.ok) {
        const data = await res.json();
        setVersions(data.versions || []);
        setRefNumber(data.reference_number || "");
      } else {
        toast({
          title: "Error",
          description: "Failed to load version history",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error fetching versions:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDiff = async (version: Version) => {
    setSelectedVersion(version);
    setLoadingDiff(true);
    setShowDiffDialog(true);
    
    try {
      const res = await fetch(
        `${API_BASE}/lc-builder/applications/${applicationId}/versions/${version.id}/diff`,
        {
          headers: {
            Authorization: `Bearer ${session?.access_token}`,
          },
        }
      );

      if (res.ok) {
        const data = await res.json();
        setDiffData(data);
      }
    } catch (error) {
      console.error("Error fetching diff:", error);
    } finally {
      setLoadingDiff(false);
    }
  };

  const handleCreateVersion = async () => {
    setCreatingVersion(true);
    try {
      const res = await fetch(
        `${API_BASE}/lc-builder/applications/${applicationId}/versions`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.access_token}`,
          },
        }
      );

      if (res.ok) {
        const data = await res.json();
        toast({
          title: "Version Created",
          description: `Version ${data.version_number} saved successfully`,
        });
        fetchVersions();
      } else {
        throw new Error("Failed to create version");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create version",
        variant: "destructive",
      });
    } finally {
      setCreatingVersion(false);
    }
  };

  const handleRestore = async () => {
    if (!restoreVersion) return;
    
    setRestoring(true);
    try {
      const res = await fetch(
        `${API_BASE}/lc-builder/applications/${applicationId}/versions/${restoreVersion.id}/restore`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session?.access_token}`,
          },
        }
      );

      if (res.ok) {
        const data = await res.json();
        toast({
          title: "Restored",
          description: `Application restored to version ${data.restored_to_version}. Backup created as version ${data.backup_version}.`,
        });
        setRestoreVersion(null);
        fetchVersions();
      } else {
        throw new Error("Failed to restore");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to restore version",
        variant: "destructive",
      });
    } finally {
      setRestoring(false);
    }
  };

  const formatDate = (isoString: string) => {
    return new Date(isoString).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const renderDiffValue = (value: any): string => {
    if (value === null || value === undefined) return "—";
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate(-1)}
              >
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <div>
                <h1 className="text-xl font-bold text-white flex items-center gap-2">
                  <History className="h-5 w-5 text-emerald-400" />
                  Version History
                </h1>
                <p className="text-sm text-slate-400">
                  {refNumber || "LC Application"} • {versions.length} version{versions.length !== 1 ? "s" : ""}
                </p>
              </div>
            </div>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700"
              onClick={handleCreateVersion}
              disabled={creatingVersion}
            >
              {creatingVersion ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Save Current Version
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
          </div>
        ) : versions.length === 0 ? (
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="py-12 text-center">
              <History className="h-12 w-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400 mb-4">No versions saved yet</p>
              <p className="text-sm text-slate-500 mb-6">
                Create a version to start tracking changes to this LC application.
              </p>
              <Button
                className="bg-emerald-600 hover:bg-emerald-700"
                onClick={handleCreateVersion}
                disabled={creatingVersion}
              >
                Create First Version
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {versions.map((version, index) => (
              <Card
                key={version.id}
                className={cn(
                  "bg-slate-900/50 border-slate-800 hover:border-slate-700 transition-colors",
                  index === 0 && "border-emerald-500/50"
                )}
              >
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-slate-800 flex items-center justify-center">
                        <span className="text-lg font-bold text-white">
                          v{version.version_number}
                        </span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-white">
                            {version.change_summary}
                          </p>
                          {index === 0 && (
                            <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                              Latest
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-slate-400 mt-1">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDate(version.created_at)}
                          </span>
                          {version.created_by && (
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              User
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchDiff(version)}
                      >
                        <GitCompare className="h-4 w-4 mr-1" />
                        View Changes
                      </Button>
                      {index !== 0 && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setRestoreVersion(version)}
                        >
                          <RotateCcw className="h-4 w-4 mr-1" />
                          Restore
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Diff Dialog */}
      <Dialog open={showDiffDialog} onOpenChange={setShowDiffDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              Version {selectedVersion?.version_number} Changes
            </DialogTitle>
            <DialogDescription>
              {diffData?.compare_to
                ? `Comparing to version ${diffData.compare_to.version_number}`
                : "Initial version - all fields shown"}
            </DialogDescription>
          </DialogHeader>

          {loadingDiff ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-emerald-400" />
            </div>
          ) : diffData?.diffs.length === 0 ? (
            <div className="text-center py-8 text-slate-400">
              No changes detected
            </div>
          ) : (
            <div className="space-y-3">
              {diffData?.diffs.map((diff, index) => (
                <div
                  key={index}
                  className={cn(
                    "p-3 rounded-lg border",
                    diff.change_type === "added" && "bg-emerald-500/10 border-emerald-500/30",
                    diff.change_type === "removed" && "bg-red-500/10 border-red-500/30",
                    diff.change_type === "modified" && "bg-amber-500/10 border-amber-500/30"
                  )}
                >
                  <div className="flex items-center gap-2 mb-2">
                    {diff.change_type === "added" && (
                      <Plus className="h-4 w-4 text-emerald-400" />
                    )}
                    {diff.change_type === "removed" && (
                      <Minus className="h-4 w-4 text-red-400" />
                    )}
                    {diff.change_type === "modified" && (
                      <RefreshCw className="h-4 w-4 text-amber-400" />
                    )}
                    <span className="font-medium text-white">{diff.label}</span>
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-xs",
                        diff.change_type === "added" && "border-emerald-500/50 text-emerald-400",
                        diff.change_type === "removed" && "border-red-500/50 text-red-400",
                        diff.change_type === "modified" && "border-amber-500/50 text-amber-400"
                      )}
                    >
                      {diff.change_type}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-slate-500 text-xs mb-1">Previous</p>
                      <p className={cn(
                        "text-slate-300",
                        diff.change_type === "added" && "text-slate-500"
                      )}>
                        {renderDiffValue(diff.old_value)}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500 text-xs mb-1">New</p>
                      <p className={cn(
                        "text-white",
                        diff.change_type === "removed" && "text-slate-500"
                      )}>
                        {renderDiffValue(diff.new_value)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Restore Confirmation Dialog */}
      <Dialog open={!!restoreVersion} onOpenChange={() => setRestoreVersion(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Restore Version {restoreVersion?.version_number}?</DialogTitle>
            <DialogDescription>
              This will restore your LC application to the state it was in at version {restoreVersion?.version_number}.
              A backup of the current state will be created automatically.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreVersion(null)}>
              Cancel
            </Button>
            <Button
              className="bg-amber-600 hover:bg-amber-700"
              onClick={handleRestore}
              disabled={restoring}
            >
              {restoring ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4 mr-2" />
              )}
              Restore
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

