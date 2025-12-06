/**
 * Shared With Me Page
 * 
 * Shows all LC applications shared with the current user.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users,
  FileText,
  Eye,
  Edit,
  MessageSquare,
  CheckCircle,
  Clock,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface SharedApplication {
  share_id: string;
  lc_id: string;
  reference_number: string;
  name: string | null;
  status: string;
  amount: number;
  currency: string;
  beneficiary_name: string;
  permission: string;
  shared_by: string;
  shared_at: string;
}

const permissionIcons: Record<string, React.ReactNode> = {
  view: <Eye className="h-4 w-4" />,
  comment: <MessageSquare className="h-4 w-4" />,
  edit: <Edit className="h-4 w-4" />,
  review: <CheckCircle className="h-4 w-4" />,
};

const permissionColors: Record<string, string> = {
  view: "bg-slate-500",
  comment: "bg-blue-500",
  edit: "bg-amber-500",
  review: "bg-emerald-500",
  admin: "bg-purple-500",
};

const statusColors: Record<string, string> = {
  draft: "bg-slate-500",
  review: "bg-amber-500",
  submitted: "bg-blue-500",
  approved: "bg-emerald-500",
  rejected: "bg-red-500",
  amended: "bg-purple-500",
};

export default function SharedWithMePage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { session } = useAuth();

  const [applications, setApplications] = useState<SharedApplication[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (session?.access_token) {
      fetchSharedApplications();
    }
  }, [session?.access_token]);

  const fetchSharedApplications = async () => {
    try {
      const res = await fetch(`${API_BASE}/lc-builder/shared-with-me`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });

      if (res.ok) {
        const data = await res.json();
        setApplications(data.shared_applications || []);
      }
    } catch (error) {
      console.error("Error fetching shared applications:", error);
      toast({
        title: "Error",
        description: "Failed to load shared applications",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleView = (lcId: string, permission: string) => {
    if (permission === "view") {
      // View only - could show a read-only version
      navigate(`/lc-builder/dashboard/workflow/${lcId}`);
    } else {
      // Edit/comment/review access
      navigate(`/lc-builder/dashboard/edit/${lcId}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <Users className="h-5 w-5 text-emerald-400" />
                Shared With Me
              </h1>
              <p className="text-sm text-slate-400">
                LC applications shared by colleagues
              </p>
            </div>
            <Badge variant="outline" className="text-emerald-400 border-emerald-400">
              {applications.length} Application{applications.length !== 1 ? "s" : ""}
            </Badge>
          </div>
        </div>
      </div>

      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
          </div>
        ) : applications.length === 0 ? (
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="flex flex-col items-center py-12">
              <Users className="h-16 w-16 text-slate-600 mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">
                No Shared Applications
              </h3>
              <p className="text-slate-400 text-center max-w-md">
                When colleagues share LC applications with you, they will appear here.
                You'll be able to view, comment, or edit based on the permissions granted.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {applications.map((app) => (
              <Card
                key={app.share_id}
                className="bg-slate-800 border-slate-700 hover:border-emerald-500/50 transition-colors cursor-pointer"
                onClick={() => handleView(app.lc_id, app.permission)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <Badge className={cn(statusColors[app.status], "text-white")}>
                      {app.status}
                    </Badge>
                    <Badge
                      variant="outline"
                      className={cn(
                        "flex items-center gap-1",
                        permissionColors[app.permission],
                        "text-white border-0"
                      )}
                    >
                      {permissionIcons[app.permission]}
                      {app.permission}
                    </Badge>
                  </div>
                  <CardTitle className="text-white text-lg mt-2">
                    {app.reference_number}
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    {app.name || "Untitled"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Amount</span>
                      <span className="text-emerald-400 font-medium">
                        {app.currency} {app.amount?.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Beneficiary</span>
                      <span className="text-white">{app.beneficiary_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Shared by</span>
                      <span className="text-white">{app.shared_by}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Shared</span>
                      <span className="text-slate-300">
                        {new Date(app.shared_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

