/**
 * Company Branding Settings
 * 
 * Configure company logo, letterhead, and document styling
 */

import { useState, useEffect } from "react";
import {
  Building2,
  Upload,
  Save,
  Loader2,
  Palette,
  FileText,
  CreditCard,
  Stamp,
  Check,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface BrandingData {
  company_name: string;
  company_address: string;
  company_phone: string;
  company_email: string;
  company_website: string;
  tax_id: string;
  registration_number: string;
  export_license: string;
  bank_name: string;
  bank_account: string;
  bank_swift: string;
  bank_address: string;
  primary_color: string;
  secondary_color: string;
  signatory_name: string;
  signatory_title: string;
  footer_text: string;
  logo_url: string;
  signature_url: string;
  stamp_url: string;
}

export function BrandingSettings() {
  const { toast } = useToast();
  const { user } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [branding, setBranding] = useState<BrandingData>({
    company_name: "",
    company_address: "",
    company_phone: "",
    company_email: "",
    company_website: "",
    tax_id: "",
    registration_number: "",
    export_license: "",
    bank_name: "",
    bank_account: "",
    bank_swift: "",
    bank_address: "",
    primary_color: "#1e40af",
    secondary_color: "#64748b",
    signatory_name: "",
    signatory_title: "",
    footer_text: "",
    logo_url: "",
    signature_url: "",
    stamp_url: "",
  });

  useEffect(() => {
    fetchBranding();
  }, []);

  const fetchBranding = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/doc-generator/branding`, {
        headers: {
          Authorization: `Bearer ${user?.access_token || ""}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setBranding((prev) => ({ ...prev, ...data }));
      }
    } catch (error) {
      console.error("Error fetching branding:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/doc-generator/branding`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.access_token || ""}`,
        },
        body: JSON.stringify(branding),
      });
      
      if (!response.ok) throw new Error("Failed to save");
      
      toast({
        title: "Settings Saved",
        description: "Your company branding has been updated.",
      });
    } catch (error) {
      toast({
        title: "Save Failed",
        description: "Could not save settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field: keyof BrandingData, value: string) => {
    setBranding((prev) => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Company Branding</h1>
          <p className="text-muted-foreground">
            Configure how your documents look
          </p>
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Save Changes
        </Button>
      </div>

      <div className="grid gap-6">
        {/* Company Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Company Information
            </CardTitle>
            <CardDescription>
              This appears on your generated documents
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Company Name</Label>
                <Input
                  value={branding.company_name}
                  onChange={(e) => handleChange("company_name", e.target.value)}
                  placeholder="Your Company Ltd."
                />
              </div>
              <div className="space-y-2">
                <Label>Website</Label>
                <Input
                  value={branding.company_website}
                  onChange={(e) => handleChange("company_website", e.target.value)}
                  placeholder="www.yourcompany.com"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Address</Label>
              <Textarea
                value={branding.company_address}
                onChange={(e) => handleChange("company_address", e.target.value)}
                placeholder="123 Business Street, City, Country"
                rows={3}
              />
            </div>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input
                  value={branding.company_phone}
                  onChange={(e) => handleChange("company_phone", e.target.value)}
                  placeholder="+1 234 567 8900"
                />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input
                  value={branding.company_email}
                  onChange={(e) => handleChange("company_email", e.target.value)}
                  placeholder="export@yourcompany.com"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Registration Details */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Registration Details
            </CardTitle>
            <CardDescription>
              Legal identifiers for your company
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Tax ID / VAT Number</Label>
                <Input
                  value={branding.tax_id}
                  onChange={(e) => handleChange("tax_id", e.target.value)}
                  placeholder="VAT123456789"
                />
              </div>
              <div className="space-y-2">
                <Label>Registration Number</Label>
                <Input
                  value={branding.registration_number}
                  onChange={(e) => handleChange("registration_number", e.target.value)}
                  placeholder="REG-2024-001"
                />
              </div>
              <div className="space-y-2">
                <Label>Export License (IEC/ERC)</Label>
                <Input
                  value={branding.export_license}
                  onChange={(e) => handleChange("export_license", e.target.value)}
                  placeholder="IEC0123456789"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Bank Details */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Bank Details
            </CardTitle>
            <CardDescription>
              For commercial invoices and payment instructions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Bank Name</Label>
                <Input
                  value={branding.bank_name}
                  onChange={(e) => handleChange("bank_name", e.target.value)}
                  placeholder="International Bank Ltd."
                />
              </div>
              <div className="space-y-2">
                <Label>SWIFT/BIC Code</Label>
                <Input
                  value={branding.bank_swift}
                  onChange={(e) => handleChange("bank_swift", e.target.value)}
                  placeholder="INTLBANK"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Account Number</Label>
              <Input
                value={branding.bank_account}
                onChange={(e) => handleChange("bank_account", e.target.value)}
                placeholder="1234567890"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Bank Address</Label>
              <Textarea
                value={branding.bank_address}
                onChange={(e) => handleChange("bank_address", e.target.value)}
                placeholder="Bank Street, Financial District, City"
                rows={2}
              />
            </div>
          </CardContent>
        </Card>

        {/* Signature & Stamp */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Stamp className="h-5 w-5" />
              Signature & Authorization
            </CardTitle>
            <CardDescription>
              Details for authorized signatory
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Signatory Name</Label>
                <Input
                  value={branding.signatory_name}
                  onChange={(e) => handleChange("signatory_name", e.target.value)}
                  placeholder="John Smith"
                />
              </div>
              <div className="space-y-2">
                <Label>Title / Designation</Label>
                <Input
                  value={branding.signatory_title}
                  onChange={(e) => handleChange("signatory_title", e.target.value)}
                  placeholder="Export Manager"
                />
              </div>
            </div>
            
            <Separator />
            
            <div className="grid md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Company Logo</Label>
                <div className="border-2 border-dashed rounded-lg p-4 text-center hover:bg-muted/50 cursor-pointer transition-colors">
                  {branding.logo_url ? (
                    <div className="flex items-center justify-center gap-2">
                      <Check className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Logo uploaded</span>
                    </div>
                  ) : (
                    <>
                      <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                      <p className="text-sm text-muted-foreground">Upload Logo</p>
                      <p className="text-xs text-muted-foreground">PNG, JPG (max 500KB)</p>
                    </>
                  )}
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Signature Image</Label>
                <div className="border-2 border-dashed rounded-lg p-4 text-center hover:bg-muted/50 cursor-pointer transition-colors">
                  {branding.signature_url ? (
                    <div className="flex items-center justify-center gap-2">
                      <Check className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Signature uploaded</span>
                    </div>
                  ) : (
                    <>
                      <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                      <p className="text-sm text-muted-foreground">Upload Signature</p>
                      <p className="text-xs text-muted-foreground">PNG with transparency</p>
                    </>
                  )}
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Company Stamp</Label>
                <div className="border-2 border-dashed rounded-lg p-4 text-center hover:bg-muted/50 cursor-pointer transition-colors">
                  {branding.stamp_url ? (
                    <div className="flex items-center justify-center gap-2">
                      <Check className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Stamp uploaded</span>
                    </div>
                  ) : (
                    <>
                      <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                      <p className="text-sm text-muted-foreground">Upload Stamp</p>
                      <p className="text-xs text-muted-foreground">PNG with transparency</p>
                    </>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Styling */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              Document Styling
            </CardTitle>
            <CardDescription>
              Colors and footer text for your documents
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Primary Color</Label>
                <div className="flex gap-2">
                  <Input
                    type="color"
                    value={branding.primary_color}
                    onChange={(e) => handleChange("primary_color", e.target.value)}
                    className="w-16 h-10 p-1 cursor-pointer"
                  />
                  <Input
                    value={branding.primary_color}
                    onChange={(e) => handleChange("primary_color", e.target.value)}
                    placeholder="#1e40af"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Secondary Color</Label>
                <div className="flex gap-2">
                  <Input
                    type="color"
                    value={branding.secondary_color}
                    onChange={(e) => handleChange("secondary_color", e.target.value)}
                    className="w-16 h-10 p-1 cursor-pointer"
                  />
                  <Input
                    value={branding.secondary_color}
                    onChange={(e) => handleChange("secondary_color", e.target.value)}
                    placeholder="#64748b"
                  />
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Document Footer Text</Label>
              <Textarea
                value={branding.footer_text}
                onChange={(e) => handleChange("footer_text", e.target.value)}
                placeholder="This document is computer generated and valid without signature. For any queries, please contact..."
                rows={3}
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default BrandingSettings;

