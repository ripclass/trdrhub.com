/**
 * Import from LCopilot
 * 
 * Modal to select an LCopilot session and import data
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Download,
  CheckCircle,
  AlertCircle,
  Loader2,
  Search,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface LCopilotSession {
  id: string;
  created_at: string;
  lc_number: string;
  beneficiary_name: string;
  applicant_name: string;
  lc_amount: number;
  currency: string;
  status: string;
}

interface ImportFromLCopilotProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportComplete?: (docSetId: string) => void;
}

export function ImportFromLCopilot({
  open,
  onOpenChange,
  onImportComplete,
}: ImportFromLCopilotProps) {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  
  const [sessions, setSessions] = useState<LCopilotSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [includeGoods, setIncludeGoods] = useState(true);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  // Fetch LCopilot sessions
  useEffect(() => {
    if (open) {
      fetchSessions();
    }
  }, [open]);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/lcopilot/sessions?limit=20`, {
        headers: {
          Authorization: `Bearer ${user?.access_token || ""}`,
        },
      });
      
      if (!response.ok) throw new Error("Failed to fetch sessions");
      
      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error("Error fetching sessions:", error);
      // Show demo data if API fails
      setSessions([
        {
          id: "demo-1",
          created_at: new Date().toISOString(),
          lc_number: "LC/2024/001234",
          beneficiary_name: "Demo Exporter Ltd",
          applicant_name: "Demo Importer Inc",
          lc_amount: 50000,
          currency: "USD",
          status: "completed",
        },
        {
          id: "demo-2",
          created_at: new Date(Date.now() - 86400000).toISOString(),
          lc_number: "LC/2024/005678",
          beneficiary_name: "Global Trade Co",
          applicant_name: "International Buyers",
          lc_amount: 125000,
          currency: "USD",
          status: "completed",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!selectedSession) return;
    
    setImporting(true);
    try {
      const response = await fetch(`${API_BASE}/doc-generator/import-from-lcopilot`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.access_token || ""}`,
        },
        body: JSON.stringify({
          session_id: selectedSession,
          include_goods: includeGoods,
        }),
      });
      
      if (!response.ok) throw new Error("Failed to import LC data");
      
      const data = await response.json();
      
      toast({
        title: "LC Data Imported!",
        description: `Document set created from LC ${data.lc_number || ""}`,
      });
      
      onOpenChange(false);
      
      if (onImportComplete) {
        onImportComplete(data.id);
      } else {
        navigate(`/doc-generator/dashboard/${data.id}`);
      }
    } catch (error) {
      console.error("Error importing:", error);
      toast({
        title: "Import Failed",
        description: "Could not import LC data. Please try again.",
        variant: "destructive",
      });
    } finally {
      setImporting(false);
    }
  };

  const filteredSessions = sessions.filter(
    (s) =>
      s.lc_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.beneficiary_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.applicant_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl bg-[#00261C] border-[#EDF5F2]/10 text-[#EDF5F2]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white font-display">
            <Download className="h-5 w-5 text-[#B2F273]" />
            Import from LCopilot
          </DialogTitle>
          <DialogDescription className="text-[#EDF5F2]/60">
            Select a validated LC to pre-fill document data
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#EDF5F2]/40" />
            <Input
              placeholder="Search by LC number, beneficiary, or applicant..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 bg-[#00382E]/50 border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/40"
            />
          </div>

          {/* Sessions List */}
          <div className="border border-[#EDF5F2]/10 rounded-lg max-h-[300px] overflow-y-auto bg-[#00382E]/30">
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-[#B2F273]" />
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center">
                <FileText className="h-12 w-12 text-[#EDF5F2]/20 mb-2" />
                <p className="text-sm text-[#EDF5F2]/60">
                  No validated LCs found
                </p>
                <p className="text-xs text-[#EDF5F2]/40 mt-1">
                  Validate an LC in LCopilot first
                </p>
              </div>
            ) : (
              <div className="divide-y divide-[#EDF5F2]/10">
                {filteredSessions.map((session) => (
                  <div
                    key={session.id}
                    className={`p-4 cursor-pointer hover:bg-[#00382E] transition-colors ${
                      selectedSession === session.id ? "bg-[#B2F273]/10 border-l-2 border-l-[#B2F273]" : ""
                    }`}
                    onClick={() => setSelectedSession(session.id)}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-white">{session.lc_number}</span>
                          <Badge variant={session.status === "completed" ? "default" : "secondary"} className="bg-[#EDF5F2]/10 text-[#EDF5F2] hover:bg-[#EDF5F2]/20">
                            {session.status}
                          </Badge>
                        </div>
                        <p className="text-sm text-[#EDF5F2]/60 mt-1">
                          {session.beneficiary_name} → {session.applicant_name}
                        </p>
                        <p className="text-sm font-medium mt-1 text-[#EDF5F2]/80">
                          {session.currency} {session.lc_amount?.toLocaleString()}
                        </p>
                      </div>
                      {selectedSession === session.id && (
                        <CheckCircle className="h-5 w-5 text-[#B2F273]" />
                      )}
                    </div>
                    <p className="text-xs text-[#EDF5F2]/40 mt-2">
                      {new Date(session.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Options */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="include-goods"
              checked={includeGoods}
              onCheckedChange={(checked) => setIncludeGoods(checked === true)}
              className="border-[#EDF5F2]/40 data-[state=checked]:bg-[#B2F273] data-[state=checked]:text-[#00261C]"
            />
            <Label htmlFor="include-goods" className="text-sm text-[#EDF5F2]/80">
              Include goods description as line item
            </Label>
          </div>

          {/* Info */}
          <div className="flex items-start gap-2 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <AlertCircle className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-200">
              <p className="font-medium text-blue-100">What gets imported:</p>
              <ul className="list-disc list-inside mt-1 text-blue-300/80">
                <li>LC number, date, amount, currency</li>
                <li>Beneficiary and applicant details</li>
                <li>Ports, incoterms, and shipping details</li>
                <li>Goods description (as line item)</li>
              </ul>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t border-[#EDF5F2]/10">
            <Button variant="outline" onClick={() => onOpenChange(false)} className="border-[#EDF5F2]/10 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 bg-transparent">
              Cancel
            </Button>
            <Button
              onClick={handleImport}
              disabled={!selectedSession || importing}
              className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold"
            >
              {importing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 mr-2" />
                  Import LC Data
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default ImportFromLCopilot;

