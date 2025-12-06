/**
 * HS Code Classification History
 */
import { useState, useEffect } from "react";
import { History, Package, Search, Trash2, Star, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface Classification {
  id: string;
  product_description: string;
  product_name?: string;
  hs_code: string;
  hs_code_description: string;
  import_country: string;
  export_country?: string;
  confidence_score: number;
  mfn_rate?: number;
  project_name?: string;
  tags: string[];
  is_verified: boolean;
  created_at: string;
}

export default function HSCodeHistory() {
  const { session } = useAuth();
  const { toast } = useToast();
  const [classifications, setClassifications] = useState<Classification[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (session?.access_token) {
      fetchHistory();
    }
  }, [session?.access_token]);

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API_BASE}/hs-code/history?limit=100`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setClassifications(data.classifications || []);
        setTotal(data.total || 0);
      }
    } catch (error) {
      console.error("Failed to fetch history:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/hs-code/history/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (response.ok) {
        setClassifications((prev) => prev.filter((c) => c.id !== id));
        toast({ title: "Deleted", description: "Classification removed from history" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to delete", variant: "destructive" });
    }
  };

  const getConfidenceBadge = (score: number) => {
    if (score >= 0.9) return "bg-emerald-500/20 text-emerald-400";
    if (score >= 0.7) return "bg-amber-500/20 text-amber-400";
    return "bg-red-500/20 text-red-400";
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <History className="h-5 w-5 text-emerald-400" />
            My Classifications
          </h1>
          <p className="text-sm text-slate-400">
            View and manage your classification history ({total} total)
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {loading ? (
          <div className="text-center py-12">
            <p className="text-slate-400">Loading history...</p>
          </div>
        ) : classifications.length === 0 ? (
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="py-12 text-center">
              <Package className="h-12 w-12 mx-auto text-slate-600 mb-4" />
              <p className="text-slate-400 mb-4">No classifications yet</p>
              <Link to="/hs-code/dashboard/classify">
                <Button className="bg-emerald-600">
                  <Search className="h-4 w-4 mr-2" />
                  Start Classifying
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-0">
              <div className="divide-y divide-slate-700">
                {classifications.map((item) => (
                  <div key={item.id} className="p-4 hover:bg-slate-700/50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className="bg-emerald-500/20 text-emerald-400">
                            {item.hs_code}
                          </Badge>
                          <Badge className={cn("text-xs", getConfidenceBadge(item.confidence_score))}>
                            {Math.round(item.confidence_score * 100)}%
                          </Badge>
                          {item.is_verified && (
                            <Badge variant="outline" className="border-blue-500 text-blue-400">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Verified
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-white font-medium truncate">
                          {item.product_description}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          {item.import_country} • {new Date(item.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(item.id)}
                        className="text-slate-400 hover:text-red-400"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

