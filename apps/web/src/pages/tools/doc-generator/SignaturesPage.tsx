/**
 * Digital Signatures Page
 * 
 * Configure and apply digital signatures to documents
 */

import { useState, useEffect, useRef } from "react";
import {
  PenTool,
  FileSignature,
  Upload,
  Loader2,
  CheckCircle,
  ExternalLink,
  AlertCircle,
  Stamp,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface SignatureProvider {
  name: string;
  configured: boolean;
  description: string;
}

export function SignaturesPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  
  const [providers, setProviders] = useState<string[]>(["local"]);
  const [docusignConfigured, setDocusignConfigured] = useState(false);
  const [adobeConfigured, setAdobeConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Local signature
  const [signatureImage, setSignatureImage] = useState<string | null>(null);
  const [stampImage, setStampImage] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      const response = await fetch(`${API_BASE}/doc-generator/advanced/signatures/providers`, {
        headers: { Authorization: `Bearer ${user?.access_token || ""}` },
      });
      if (response.ok) {
        const data = await response.json();
        setProviders(data.providers);
        setDocusignConfigured(data.docusign_configured);
        setAdobeConfigured(data.adobe_configured);
      }
    } catch (error) {
      console.error("Error fetching providers:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>, type: "signature" | "stamp") => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
      const base64 = event.target?.result as string;
      if (type === "signature") {
        setSignatureImage(base64);
      } else {
        setStampImage(base64);
      }
    };
    reader.readAsDataURL(file);
  };

  // Canvas drawing for signature
  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDrawing(true);
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  };

  const saveCanvasSignature = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = canvas.toDataURL("image/png");
    setSignatureImage(dataUrl);
    toast({ title: "Signature Saved", description: "Your drawn signature has been saved" });
  };

  const PROVIDER_INFO: Record<string, SignatureProvider> = {
    local: {
      name: "Local Signature",
      configured: true,
      description: "Upload or draw a signature image. Suitable for internal documents.",
    },
    docusign: {
      name: "DocuSign",
      configured: docusignConfigured,
      description: "Industry-standard e-signature. Legally binding, with audit trail.",
    },
    adobe_sign: {
      name: "Adobe Sign",
      configured: adobeConfigured,
      description: "Adobe's e-signature solution. Integrates with Adobe ecosystem.",
    },
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Digital Signatures</h1>
        <p className="text-slate-400">Configure signature methods for your documents</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-3">
          {Object.entries(PROVIDER_INFO).map(([key, info]) => (
            <Card 
              key={key}
              className={`bg-slate-900/50 border-slate-800 ${!info.configured ? 'opacity-60' : ''}`}
            >
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white flex items-center gap-2">
                    <FileSignature className="h-5 w-5" />
                    {info.name}
                  </CardTitle>
                  <Badge variant={info.configured ? "default" : "outline"}>
                    {info.configured ? "Available" : "Not Configured"}
                  </Badge>
                </div>
                <CardDescription>{info.description}</CardDescription>
              </CardHeader>
              <CardContent>
                {key === "local" && (
                  <Button variant="outline" size="sm" className="w-full">
                    Configure
                  </Button>
                )}
                {key === "docusign" && !info.configured && (
                  <Button variant="outline" size="sm" className="w-full" asChild>
                    <a href="https://developers.docusign.com/" target="_blank" rel="noopener">
                      Setup DocuSign
                      <ExternalLink className="w-3 h-3 ml-2" />
                    </a>
                  </Button>
                )}
                {key === "adobe_sign" && !info.configured && (
                  <Button variant="outline" size="sm" className="w-full" asChild>
                    <a href="https://acrobat.adobe.com/us/en/sign.html" target="_blank" rel="noopener">
                      Setup Adobe Sign
                      <ExternalLink className="w-3 h-3 ml-2" />
                    </a>
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Local Signature Configuration */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Local Signature Settings</CardTitle>
          <CardDescription>
            Upload or draw your signature for embedding in documents
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="draw" className="space-y-4">
            <TabsList className="bg-slate-800">
              <TabsTrigger value="draw">
                <PenTool className="w-4 h-4 mr-2" />
                Draw
              </TabsTrigger>
              <TabsTrigger value="upload">
                <Upload className="w-4 h-4 mr-2" />
                Upload
              </TabsTrigger>
              <TabsTrigger value="stamp">
                <Stamp className="w-4 h-4 mr-2" />
                Company Stamp
              </TabsTrigger>
            </TabsList>

            <TabsContent value="draw" className="space-y-4">
              <div className="border-2 border-dashed border-slate-700 rounded-lg p-2">
                <canvas
                  ref={canvasRef}
                  width={400}
                  height={150}
                  className="bg-white rounded cursor-crosshair"
                  onMouseDown={startDrawing}
                  onMouseMove={draw}
                  onMouseUp={stopDrawing}
                  onMouseLeave={stopDrawing}
                />
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={clearCanvas}>Clear</Button>
                <Button onClick={saveCanvasSignature}>Save Signature</Button>
              </div>
            </TabsContent>

            <TabsContent value="upload" className="space-y-4">
              <div className="space-y-2">
                <Label>Upload Signature Image</Label>
                <Input
                  type="file"
                  accept="image/png,image/jpeg"
                  onChange={(e) => handleImageUpload(e, "signature")}
                  className="bg-slate-800 border-slate-700"
                />
                <p className="text-xs text-slate-400">
                  Upload a PNG or JPEG with transparent background for best results
                </p>
              </div>
              
              {signatureImage && (
                <div className="mt-4">
                  <Label>Preview:</Label>
                  <div className="mt-2 p-4 bg-white rounded inline-block">
                    <img 
                      src={signatureImage} 
                      alt="Signature preview" 
                      className="max-h-20"
                    />
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="stamp" className="space-y-4">
              <div className="space-y-2">
                <Label>Upload Company Stamp</Label>
                <Input
                  type="file"
                  accept="image/png,image/jpeg"
                  onChange={(e) => handleImageUpload(e, "stamp")}
                  className="bg-slate-800 border-slate-700"
                />
                <p className="text-xs text-slate-400">
                  Upload your company seal/stamp image
                </p>
              </div>
              
              {stampImage && (
                <div className="mt-4">
                  <Label>Preview:</Label>
                  <div className="mt-2 p-4 bg-white rounded inline-block">
                    <img 
                      src={stampImage} 
                      alt="Stamp preview" 
                      className="max-h-24"
                    />
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Integration Status */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">E-Signature Integration Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${docusignConfigured ? 'bg-green-500' : 'bg-slate-500'}`} />
              <span className="text-white">DocuSign API</span>
            </div>
            <Badge variant={docusignConfigured ? "default" : "secondary"}>
              {docusignConfigured ? "Connected" : "Not Connected"}
            </Badge>
          </div>
          
          <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${adobeConfigured ? 'bg-green-500' : 'bg-slate-500'}`} />
              <span className="text-white">Adobe Sign API</span>
            </div>
            <Badge variant={adobeConfigured ? "default" : "secondary"}>
              {adobeConfigured ? "Connected" : "Not Connected"}
            </Badge>
          </div>
          
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5" />
              <div>
                <p className="text-sm text-amber-200">
                  E-signature integrations require API credentials. Contact support or configure in Settings.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default SignaturesPage;

