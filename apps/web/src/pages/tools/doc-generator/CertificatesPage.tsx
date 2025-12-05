/**
 * Certificates Page
 * 
 * Generate GSP Form A, EUR.1, and other preferential origin certificates
 */

import { useState, useEffect } from "react";
import {
  Award,
  FileText,
  Globe,
  Download,
  Loader2,
  Info,
  CheckCircle,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface DocumentSetSummary {
  id: string;
  name: string;
  invoice_number: string;
  beneficiary_name: string;
  created_at: string;
}

const CERTIFICATE_TYPES = [
  {
    id: "gsp_form_a",
    name: "GSP Form A",
    fullName: "Generalized System of Preferences - Certificate of Origin",
    description: "For exports to developed countries (US, EU, Japan, etc.) with preferential tariff treatment",
    color: "green",
    acceptedBy: ["United States", "European Union", "Japan", "Canada", "Australia", "Switzerland", "Norway"],
  },
  {
    id: "eur1",
    name: "EUR.1",
    fullName: "Movement Certificate EUR.1",
    description: "For trade between EU and partner countries with free trade agreements",
    color: "blue",
    acceptedBy: ["EU Member States", "Turkey", "Switzerland", "EFTA Countries", "Mediterranean Partners"],
  },
];

export function CertificatesPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  
  const [documentSets, setDocumentSets] = useState<DocumentSetSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocSet, setSelectedDocSet] = useState<string>("");
  const [selectedCertType, setSelectedCertType] = useState<string>("");
  const [generating, setGenerating] = useState(false);
  
  // Additional data for certificate
  const [originCriterion, setOriginCriterion] = useState("P");
  const [place, setPlace] = useState("");

  useEffect(() => {
    fetchDocumentSets();
  }, []);

  const fetchDocumentSets = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/doc-generator/document-sets`, {
        headers: { Authorization: `Bearer ${user?.access_token || ""}` },
      });
      if (response.ok) {
        const data = await response.json();
        setDocumentSets(data.document_sets || []);
      }
    } catch (error) {
      console.error("Error fetching document sets:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedDocSet || !selectedCertType) {
      toast({ 
        title: "Selection Required", 
        description: "Please select a document set and certificate type",
        variant: "destructive" 
      });
      return;
    }

    setGenerating(true);
    try {
      const response = await fetch(`${API_BASE}/api/doc-generator/advanced/certificates/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.access_token || ""}`,
        },
        body: JSON.stringify({
          document_set_id: selectedDocSet,
          certificate_type: selectedCertType,
          additional_data: {
            origin_criterion: originCriterion,
            place: place,
          }
        }),
      });

      if (!response.ok) throw new Error("Generation failed");

      // Download the PDF
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selectedCertType.toUpperCase()}_${selectedDocSet.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      toast({ 
        title: "Certificate Generated", 
        description: "Your certificate has been downloaded" 
      });
    } catch (error) {
      toast({ 
        title: "Error", 
        description: "Failed to generate certificate", 
        variant: "destructive" 
      });
    } finally {
      setGenerating(false);
    }
  };

  const selectedCert = CERTIFICATE_TYPES.find(c => c.id === selectedCertType);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Origin Certificates</h1>
        <p className="text-slate-400">
          Generate GSP Form A, EUR.1, and other preferential origin certificates
        </p>
      </div>

      {/* Certificate Types */}
      <div className="grid gap-4 md:grid-cols-2">
        {CERTIFICATE_TYPES.map((cert) => (
          <Card 
            key={cert.id}
            className={`bg-slate-900/50 border-slate-800 cursor-pointer transition-all ${
              selectedCertType === cert.id 
                ? 'ring-2 ring-blue-500 border-blue-500' 
                : 'hover:border-slate-700'
            }`}
            onClick={() => setSelectedCertType(cert.id)}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white flex items-center gap-2">
                  <Award className={`h-5 w-5 text-${cert.color}-500`} />
                  {cert.name}
                </CardTitle>
                {selectedCertType === cert.id && (
                  <CheckCircle className="h-5 w-5 text-blue-500" />
                )}
              </div>
              <CardDescription>{cert.fullName}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-400 mb-4">{cert.description}</p>
              <div className="flex flex-wrap gap-1">
                {cert.acceptedBy.slice(0, 4).map((country) => (
                  <Badge key={country} variant="outline" className="text-xs">
                    {country}
                  </Badge>
                ))}
                {cert.acceptedBy.length > 4 && (
                  <Badge variant="outline" className="text-xs">
                    +{cert.acceptedBy.length - 4} more
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Separator className="bg-slate-800" />

      {/* Generation Form */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Generate Certificate</CardTitle>
          <CardDescription>
            Select a document set and configure certificate details
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Document Set Selection */}
          <div className="space-y-2">
            <Label>Document Set</Label>
            {loading ? (
              <div className="flex items-center gap-2 text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading document sets...
              </div>
            ) : (
              <Select value={selectedDocSet} onValueChange={setSelectedDocSet}>
                <SelectTrigger className="bg-slate-800 border-slate-700">
                  <SelectValue placeholder="Select a document set" />
                </SelectTrigger>
                <SelectContent>
                  {documentSets.map((ds) => (
                    <SelectItem key={ds.id} value={ds.id}>
                      {ds.name || ds.invoice_number || ds.id.slice(0, 8)}
                      {ds.beneficiary_name && ` - ${ds.beneficiary_name}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Certificate Type Display */}
          {selectedCert && (
            <div className="p-4 bg-slate-800/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Award className="h-5 w-5 text-blue-500" />
                <span className="font-medium text-white">{selectedCert.name}</span>
              </div>
              <p className="text-sm text-slate-400">{selectedCert.fullName}</p>
            </div>
          )}

          {/* Additional Fields for GSP Form A */}
          {selectedCertType === "gsp_form_a" && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Origin Criterion</Label>
                <Select value={originCriterion} onValueChange={setOriginCriterion}>
                  <SelectTrigger className="bg-slate-800 border-slate-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="P">P - Wholly obtained</SelectItem>
                    <SelectItem value="W">W - Substantially transformed</SelectItem>
                    <SelectItem value="F">F - From specified materials</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-slate-400">
                  P = Products wholly obtained in the country
                </p>
              </div>
              <div className="space-y-2">
                <Label>Place of Certification</Label>
                <Input
                  value={place}
                  onChange={(e) => setPlace(e.target.value)}
                  placeholder="e.g., Dhaka, Bangladesh"
                  className="bg-slate-800 border-slate-700"
                />
              </div>
            </div>
          )}

          {/* Info Box */}
          <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-blue-500 mt-0.5" />
              <div>
                <h4 className="font-medium text-blue-300 mb-1">Important</h4>
                <p className="text-sm text-blue-200">
                  The certificate will be generated using data from your selected document set.
                  Ensure all information is accurate before generating. Official certificates may
                  require authentication by the Chamber of Commerce.
                </p>
              </div>
            </div>
          </div>

          {/* Generate Button */}
          <Button 
            onClick={handleGenerate}
            disabled={!selectedDocSet || !selectedCertType || generating}
            className="w-full"
          >
            {generating ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Download className="w-4 h-4 mr-2" />
                Generate {selectedCert?.name || "Certificate"}
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Help Section */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Certificate Guide</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <h4 className="font-medium text-green-400">GSP Form A</h4>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>• Used for exports from developing to developed countries</li>
                <li>• Provides reduced or zero tariff rates</li>
                <li>• Must be authenticated by authorized body</li>
                <li>• Valid for 12 months from date of issue</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium text-blue-400">EUR.1 Certificate</h4>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>• For EU FTA partner country trade</li>
                <li>• Proves preferential origin of goods</li>
                <li>• Customs authority authentication required</li>
                <li>• Validity period varies by agreement</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default CertificatesPage;

