import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  FileCheck,
  Search,
  Download,
  Calendar,
  CheckCircle,
  AlertTriangle,
  Clock,
  Shield,
  RefreshCw,
} from "lucide-react";
import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface Certificate {
  id: string;
  query: string;
  type: "party" | "vessel" | "goods";
  status: "clear" | "potential_match" | "match";
  issued_at: string;
  valid_until: string;
  lists_count: number;
  expired?: boolean;
}

export default function SanctionsCertificates() {
  const [searchQuery, setSearchQuery] = useState("");
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch certificates from history API (certificates are generated from screening history)
  useEffect(() => {
    const fetchCertificates = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`${API_BASE}/sanctions/history`, {
          credentials: "include",
        });
        if (!response.ok) {
          throw new Error("Failed to fetch certificates");
        }
        const data = await response.json();
        // Transform history items to certificate format
        const historyItems = data.history || data || [];
        const certs: Certificate[] = historyItems
          .filter((item: any) => item.certificate_id)
          .map((item: any) => ({
            id: item.certificate_id,
            query: item.query,
            type: item.type,
            status: item.status,
            issued_at: item.screened_at,
            valid_until: new Date(new Date(item.screened_at).getTime() + 24 * 60 * 60 * 1000).toISOString(),
            lists_count: item.lists_screened?.length || 0,
            expired: new Date(item.screened_at).getTime() + 24 * 60 * 60 * 1000 < Date.now(),
          }));
        setCertificates(certs);
      } catch (err) {
        console.error("Failed to fetch certificates:", err);
        setError("Failed to load certificates. Please try again.");
        setCertificates([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchCertificates();
  }, []);

  const filteredCerts = certificates.filter((cert) =>
    cert.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    cert.query.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <FileCheck className="w-6 h-6 text-red-400" />
            Screening Certificates
          </h1>
          <p className="text-slate-400 mt-1">
            Download compliance certificates for your records
          </p>
        </div>
      </div>

      {/* Search */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by certificate ID or query..."
              className="pl-10 bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
            />
          </div>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="bg-gradient-to-r from-red-500/10 to-orange-500/10 border-red-500/20">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-red-400 mt-0.5" />
            <div>
              <h4 className="font-medium text-white">About Screening Certificates</h4>
              <p className="text-sm text-slate-400 mt-1">
                Certificates are valid for 24 hours from the time of screening. 
                They confirm that a screening was performed against the specified lists 
                at a specific point in time. Always re-screen before finalizing transactions.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Certificates List */}
      <div className="space-y-3">
        {filteredCerts.length === 0 ? (
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-12 text-center">
              <FileCheck className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No certificates found</h3>
              <p className="text-slate-400">
                {searchQuery ? "No certificates match your search" : "Your certificates will appear here"}
              </p>
            </CardContent>
          </Card>
        ) : (
          filteredCerts.map((cert) => (
            <Card 
              key={cert.id} 
              className={`bg-slate-900/50 border-slate-800 ${cert.expired ? "opacity-60" : ""}`}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 ${
                      cert.expired 
                        ? "bg-slate-500/20" 
                        : cert.status === "clear" 
                        ? "bg-emerald-500/20" 
                        : "bg-amber-500/20"
                    } rounded-lg flex items-center justify-center`}>
                      {cert.status === "clear" ? (
                        <CheckCircle className={`w-6 h-6 ${cert.expired ? "text-slate-500" : "text-emerald-400"}`} />
                      ) : (
                        <AlertTriangle className={`w-6 h-6 ${cert.expired ? "text-slate-500" : "text-amber-400"}`} />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm text-red-400">{cert.id}</span>
                        {cert.expired && (
                          <Badge variant="outline" className="border-slate-600 text-slate-500 text-xs">
                            Expired
                          </Badge>
                        )}
                      </div>
                      <p className="text-white font-medium mt-1">{cert.query}</p>
                      <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          Issued: {new Date(cert.issued_at).toLocaleString()}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Valid until: {new Date(cert.valid_until).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right text-sm">
                      <p className="text-slate-400">{cert.lists_count} lists screened</p>
                      <p className={`font-medium ${
                        cert.status === "clear" ? "text-emerald-400" : "text-amber-400"
                      }`}>
                        {cert.status === "clear" ? "Clear" : "Review Required"}
                      </p>
                    </div>
                    <Button 
                      variant="outline" 
                      className="border-slate-700 text-slate-400 hover:text-white"
                      disabled={cert.expired}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download PDF
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}

