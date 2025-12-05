import { useState, useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  AlertTriangle,
  Info,
  HelpCircle,
  FileText,
  Users,
  Ship,
  Package,
  FileCheck,
  CreditCard,
  Save,
  Download,
  Eye,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const API_BASE = import.meta.env.VITE_API_URL || "";

// Wizard steps
const STEPS = [
  { id: 1, title: "Basic Details", icon: FileText, description: "LC type, amount, tolerance" },
  { id: 2, title: "Parties", icon: Users, description: "Applicant & beneficiary" },
  { id: 3, title: "Shipment", icon: Ship, description: "Ports, dates, Incoterms" },
  { id: 4, title: "Goods", icon: Package, description: "Description of goods" },
  { id: 5, title: "Documents", icon: FileCheck, description: "Required documents" },
  { id: 6, title: "Payment", icon: CreditCard, description: "Terms & validity" },
];

// Standard document options
const STANDARD_DOCUMENTS = [
  { type: "commercial_invoice", label: "Commercial Invoice", defaultOriginals: 3 },
  { type: "packing_list", label: "Packing List", defaultOriginals: 3 },
  { type: "bill_of_lading", label: "Full Set Clean On Board B/L", defaultOriginals: 3 },
  { type: "certificate_of_origin", label: "Certificate of Origin", defaultOriginals: 1 },
  { type: "insurance_certificate", label: "Insurance Certificate", defaultOriginals: 1 },
  { type: "inspection_certificate", label: "Inspection Certificate", defaultOriginals: 1 },
  { type: "weight_certificate", label: "Weight Certificate", defaultOriginals: 1 },
  { type: "beneficiary_certificate", label: "Beneficiary Certificate", defaultOriginals: 1 },
];

interface FormData {
  // Step 1: Basic
  name: string;
  lc_type: string;
  currency: string;
  amount: string;
  tolerance_plus: string;
  tolerance_minus: string;
  
  // Step 2: Parties
  applicant_name: string;
  applicant_address: string;
  applicant_country: string;
  beneficiary_name: string;
  beneficiary_address: string;
  beneficiary_country: string;
  advising_bank_name: string;
  advising_bank_swift: string;
  
  // Step 3: Shipment
  port_of_loading: string;
  port_of_discharge: string;
  place_of_delivery: string;
  latest_shipment_date: string;
  incoterms: string;
  incoterms_place: string;
  partial_shipments: boolean;
  transhipment: boolean;
  
  // Step 4: Goods
  goods_description: string;
  hs_code: string;
  quantity: string;
  unit_price: string;
  
  // Step 5: Documents
  documents_required: Array<{
    document_type: string;
    copies_original: number;
    copies_copy: number;
    specific_requirements: string;
    is_required: boolean;
  }>;
  
  // Step 6: Payment
  payment_terms: string;
  usance_days: string;
  usance_from: string;
  expiry_date: string;
  expiry_place: string;
  presentation_period: string;
  confirmation_instructions: string;
  additional_conditions: string[];
}

const initialFormData: FormData = {
  name: "",
  lc_type: "documentary",
  currency: "USD",
  amount: "",
  tolerance_plus: "5",
  tolerance_minus: "5",
  
  applicant_name: "",
  applicant_address: "",
  applicant_country: "",
  beneficiary_name: "",
  beneficiary_address: "",
  beneficiary_country: "",
  advising_bank_name: "",
  advising_bank_swift: "",
  
  port_of_loading: "",
  port_of_discharge: "",
  place_of_delivery: "",
  latest_shipment_date: "",
  incoterms: "FOB",
  incoterms_place: "",
  partial_shipments: true,
  transhipment: true,
  
  goods_description: "",
  hs_code: "",
  quantity: "",
  unit_price: "",
  
  documents_required: [
    { document_type: "commercial_invoice", copies_original: 3, copies_copy: 0, specific_requirements: "", is_required: true },
    { document_type: "packing_list", copies_original: 3, copies_copy: 0, specific_requirements: "", is_required: true },
    { document_type: "bill_of_lading", copies_original: 3, copies_copy: 0, specific_requirements: "", is_required: true },
  ],
  
  payment_terms: "sight",
  usance_days: "30",
  usance_from: "bl_date",
  expiry_date: "",
  expiry_place: "",
  presentation_period: "21",
  confirmation_instructions: "without",
  additional_conditions: [],
};

export default function LCBuilderWizard() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { session, user, loading: authLoading } = useAuth();
  
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [saving, setSaving] = useState(false);
  const [validation, setValidation] = useState<any>(null);
  const [mt700Preview, setMT700Preview] = useState<any>(null);
  const [showMT700Dialog, setShowMT700Dialog] = useState(false);
  
  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate("/login?redirect=/lc-builder/wizard");
    }
  }, [authLoading, user, navigate]);
  
  // Load existing application if editing
  useEffect(() => {
    if (id && session?.access_token) {
      loadApplication(id);
    }
  }, [id, session?.access_token]);
  
  const loadApplication = async (appId: string) => {
    try {
      const response = await fetch(`${API_BASE}/lc-builder/applications/${appId}`, {
        headers: { Authorization: `Bearer ${session?.access_token || ""}` },
      });
      
      if (!response.ok) throw new Error("Failed to load application");
      
      const data = await response.json();
      setFormData({
        name: data.name || "",
        lc_type: data.lc_type || "documentary",
        currency: data.currency || "USD",
        amount: String(data.amount || ""),
        tolerance_plus: String(data.tolerance_plus || 5),
        tolerance_minus: String(data.tolerance_minus || 5),
        
        applicant_name: data.applicant?.name || "",
        applicant_address: data.applicant?.address || "",
        applicant_country: data.applicant?.country || "",
        beneficiary_name: data.beneficiary?.name || "",
        beneficiary_address: data.beneficiary?.address || "",
        beneficiary_country: data.beneficiary?.country || "",
        advising_bank_name: data.advising_bank?.name || "",
        advising_bank_swift: data.advising_bank?.swift || "",
        
        port_of_loading: data.port_of_loading || "",
        port_of_discharge: data.port_of_discharge || "",
        place_of_delivery: data.place_of_delivery || "",
        latest_shipment_date: data.latest_shipment_date?.split("T")[0] || "",
        incoterms: data.incoterms || "FOB",
        incoterms_place: data.incoterms_place || "",
        partial_shipments: data.partial_shipments ?? true,
        transhipment: data.transhipment ?? true,
        
        goods_description: data.goods_description || "",
        hs_code: data.hs_code || "",
        quantity: data.quantity || "",
        unit_price: data.unit_price || "",
        
        documents_required: data.documents_required || initialFormData.documents_required,
        
        payment_terms: data.payment_terms || "sight",
        usance_days: String(data.usance_days || 30),
        usance_from: data.usance_from || "bl_date",
        expiry_date: data.expiry_date?.split("T")[0] || "",
        expiry_place: data.expiry_place || "",
        presentation_period: String(data.presentation_period || 21),
        confirmation_instructions: data.confirmation_instructions || "without",
        additional_conditions: data.additional_conditions || [],
      });
      
      setValidation({
        is_valid: data.validation_issues?.length === 0,
        issues: data.validation_issues || [],
        risk_score: data.risk_score || 0,
        risk_details: data.risk_details || {},
      });
    } catch (error) {
      console.error("Error loading application:", error);
      toast({
        title: "Error",
        description: "Failed to load LC application",
        variant: "destructive",
      });
    }
  };
  
  const handleSave = async (isDraft = true) => {
    setSaving(true);
    try {
      const payload = {
        name: formData.name,
        lc_type: formData.lc_type,
        currency: formData.currency,
        amount: parseFloat(formData.amount) || 0,
        tolerance_plus: parseFloat(formData.tolerance_plus) || 0,
        tolerance_minus: parseFloat(formData.tolerance_minus) || 0,
        
        applicant: {
          name: formData.applicant_name,
          address: formData.applicant_address,
          country: formData.applicant_country,
        },
        beneficiary: {
          name: formData.beneficiary_name,
          address: formData.beneficiary_address,
          country: formData.beneficiary_country,
        },
        advising_bank: formData.advising_bank_name ? {
          name: formData.advising_bank_name,
          swift: formData.advising_bank_swift,
        } : null,
        
        port_of_loading: formData.port_of_loading,
        port_of_discharge: formData.port_of_discharge,
        place_of_delivery: formData.place_of_delivery,
        latest_shipment_date: formData.latest_shipment_date || null,
        incoterms: formData.incoterms,
        incoterms_place: formData.incoterms_place,
        partial_shipments: formData.partial_shipments,
        transhipment: formData.transhipment,
        
        goods_description: formData.goods_description,
        hs_code: formData.hs_code,
        quantity: formData.quantity,
        unit_price: formData.unit_price,
        
        documents_required: formData.documents_required,
        
        payment_terms: formData.payment_terms,
        usance_days: formData.payment_terms === "usance" ? parseInt(formData.usance_days) : null,
        usance_from: formData.payment_terms === "usance" ? formData.usance_from : null,
        expiry_date: formData.expiry_date || null,
        expiry_place: formData.expiry_place,
        presentation_period: parseInt(formData.presentation_period) || 21,
        confirmation_instructions: formData.confirmation_instructions,
        additional_conditions: formData.additional_conditions,
        selected_clause_ids: [],
      };
      
      const url = id
        ? `${API_BASE}/lc-builder/applications/${id}`
        : `${API_BASE}/lc-builder/applications`;
      const method = id ? "PUT" : "POST";
      
      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token || ""}`,
        },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to save");
      }
      
      const data = await response.json();
      setValidation(data.validation);
      
      toast({
        title: "Saved",
        description: id ? "LC application updated" : `Created: ${data.reference_number}`,
      });
      
      if (!id) {
        navigate(`/lc-builder/wizard/${data.id}`);
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to save application",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };
  
  const handlePreviewMT700 = async () => {
    if (!id) {
      toast({
        title: "Save First",
        description: "Please save the application before generating MT700 preview",
        variant: "destructive",
      });
      return;
    }
    
    try {
      const response = await fetch(
        `${API_BASE}/lc-builder/applications/${id}/export/mt700`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${session?.access_token || ""}` },
        }
      );
      
      if (!response.ok) throw new Error("Failed to generate MT700");
      
      const data = await response.json();
      setMT700Preview(data);
      setShowMT700Dialog(true);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to generate MT700 preview",
        variant: "destructive",
      });
    }
  };
  
  const updateFormData = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };
  
  const toggleDocument = (docType: string, checked: boolean) => {
    setFormData((prev) => {
      const docs = [...prev.documents_required];
      const existing = docs.find((d) => d.document_type === docType);
      
      if (checked && !existing) {
        const standard = STANDARD_DOCUMENTS.find((d) => d.type === docType);
        docs.push({
          document_type: docType,
          copies_original: standard?.defaultOriginals || 1,
          copies_copy: 0,
          specific_requirements: "",
          is_required: true,
        });
      } else if (!checked && existing) {
        const idx = docs.findIndex((d) => d.document_type === docType);
        if (idx >= 0) docs.splice(idx, 1);
      }
      
      return { ...prev, documents_required: docs };
    });
  };
  
  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6">
            <div>
              <Label>Application Name (Optional)</Label>
              <Input
                placeholder="e.g., Q1 2025 Cotton Import"
                value={formData.name}
                onChange={(e) => updateFormData("name", e.target.value)}
                className="bg-slate-800 border-slate-700 mt-1"
              />
            </div>
            
            <div>
              <Label>Type of Documentary Credit</Label>
              <Select
                value={formData.lc_type}
                onValueChange={(v) => updateFormData("lc_type", v)}
              >
                <SelectTrigger className="bg-slate-800 border-slate-700 mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="documentary">Irrevocable Documentary Credit</SelectItem>
                  <SelectItem value="standby">Standby Letter of Credit (SBLC)</SelectItem>
                  <SelectItem value="transferable">Transferable Credit</SelectItem>
                  <SelectItem value="revolving">Revolving Credit</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-slate-400 mt-1">
                Most common: Irrevocable Documentary Credit
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Currency</Label>
                <Select
                  value={formData.currency}
                  onValueChange={(v) => updateFormData("currency", v)}
                >
                  <SelectTrigger className="bg-slate-800 border-slate-700 mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD - US Dollar</SelectItem>
                    <SelectItem value="EUR">EUR - Euro</SelectItem>
                    <SelectItem value="GBP">GBP - British Pound</SelectItem>
                    <SelectItem value="CNY">CNY - Chinese Yuan</SelectItem>
                    <SelectItem value="JPY">JPY - Japanese Yen</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Amount</Label>
                <Input
                  type="number"
                  placeholder="500000"
                  value={formData.amount}
                  onChange={(e) => updateFormData("amount", e.target.value)}
                  className="bg-slate-800 border-slate-700 mt-1"
                />
              </div>
            </div>
            
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Label>Amount Tolerance</Label>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <HelpCircle className="h-4 w-4 text-slate-400" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">
                        Allows flexibility for quantity/amount. Standard is ±5%.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">+</span>
                    <Input
                      type="number"
                      value={formData.tolerance_plus}
                      onChange={(e) => updateFormData("tolerance_plus", e.target.value)}
                      className="bg-slate-800 border-slate-700"
                    />
                    <span className="text-slate-400">%</span>
                  </div>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">-</span>
                    <Input
                      type="number"
                      value={formData.tolerance_minus}
                      onChange={(e) => updateFormData("tolerance_minus", e.target.value)}
                      className="bg-slate-800 border-slate-700"
                    />
                    <span className="text-slate-400">%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
        
      case 2:
        return (
          <div className="space-y-6">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Applicant (Buyer)</CardTitle>
                <CardDescription>Your company details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Company Name *</Label>
                  <Input
                    placeholder="Your Company Ltd"
                    value={formData.applicant_name}
                    onChange={(e) => updateFormData("applicant_name", e.target.value)}
                    className="bg-slate-800 border-slate-700 mt-1"
                  />
                </div>
                <div>
                  <Label>Address</Label>
                  <Textarea
                    placeholder="Street address, city, postal code"
                    value={formData.applicant_address}
                    onChange={(e) => updateFormData("applicant_address", e.target.value)}
                    className="bg-slate-800 border-slate-700 mt-1"
                    rows={2}
                  />
                </div>
                <div>
                  <Label>Country</Label>
                  <Input
                    placeholder="Country"
                    value={formData.applicant_country}
                    onChange={(e) => updateFormData("applicant_country", e.target.value)}
                    className="bg-slate-800 border-slate-700 mt-1"
                  />
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Beneficiary (Seller)</CardTitle>
                <CardDescription>Supplier/Exporter details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Company Name *</Label>
                  <Input
                    placeholder="Supplier Company Name"
                    value={formData.beneficiary_name}
                    onChange={(e) => updateFormData("beneficiary_name", e.target.value)}
                    className="bg-slate-800 border-slate-700 mt-1"
                  />
                </div>
                <div>
                  <Label>Address</Label>
                  <Textarea
                    placeholder="Street address, city, postal code"
                    value={formData.beneficiary_address}
                    onChange={(e) => updateFormData("beneficiary_address", e.target.value)}
                    className="bg-slate-800 border-slate-700 mt-1"
                    rows={2}
                  />
                </div>
                <div>
                  <Label>Country</Label>
                  <Input
                    placeholder="Country"
                    value={formData.beneficiary_country}
                    onChange={(e) => updateFormData("beneficiary_country", e.target.value)}
                    className="bg-slate-800 border-slate-700 mt-1"
                  />
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Advising Bank (Optional)</CardTitle>
                <CardDescription>Bank that will advise the LC to beneficiary</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Bank Name</Label>
                    <Input
                      placeholder="Bank name"
                      value={formData.advising_bank_name}
                      onChange={(e) => updateFormData("advising_bank_name", e.target.value)}
                      className="bg-slate-800 border-slate-700 mt-1"
                    />
                  </div>
                  <div>
                    <Label>SWIFT Code</Label>
                    <Input
                      placeholder="BANKXXXX"
                      value={formData.advising_bank_swift}
                      onChange={(e) => updateFormData("advising_bank_swift", e.target.value)}
                      className="bg-slate-800 border-slate-700 mt-1"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        );
        
      case 3:
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Port of Loading *</Label>
                <Input
                  placeholder="e.g., Shanghai, China"
                  value={formData.port_of_loading}
                  onChange={(e) => updateFormData("port_of_loading", e.target.value)}
                  className="bg-slate-800 border-slate-700 mt-1"
                />
              </div>
              <div>
                <Label>Port of Discharge *</Label>
                <Input
                  placeholder="e.g., Los Angeles, USA"
                  value={formData.port_of_discharge}
                  onChange={(e) => updateFormData("port_of_discharge", e.target.value)}
                  className="bg-slate-800 border-slate-700 mt-1"
                />
              </div>
            </div>
            
            <div>
              <Label>Place of Final Destination (Optional)</Label>
              <Input
                placeholder="If different from port of discharge"
                value={formData.place_of_delivery}
                onChange={(e) => updateFormData("place_of_delivery", e.target.value)}
                className="bg-slate-800 border-slate-700 mt-1"
              />
            </div>
            
            <div>
              <Label>Latest Shipment Date *</Label>
              <Input
                type="date"
                value={formData.latest_shipment_date}
                onChange={(e) => updateFormData("latest_shipment_date", e.target.value)}
                className="bg-slate-800 border-slate-700 mt-1"
              />
              <p className="text-xs text-slate-400 mt-1">
                Allow enough time for production & booking
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Incoterms 2020</Label>
                <Select
                  value={formData.incoterms}
                  onValueChange={(v) => updateFormData("incoterms", v)}
                >
                  <SelectTrigger className="bg-slate-800 border-slate-700 mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EXW">EXW - Ex Works</SelectItem>
                    <SelectItem value="FCA">FCA - Free Carrier</SelectItem>
                    <SelectItem value="FOB">FOB - Free On Board</SelectItem>
                    <SelectItem value="CFR">CFR - Cost and Freight</SelectItem>
                    <SelectItem value="CIF">CIF - Cost, Insurance & Freight</SelectItem>
                    <SelectItem value="DAP">DAP - Delivered at Place</SelectItem>
                    <SelectItem value="DDP">DDP - Delivered Duty Paid</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Place (for Incoterms)</Label>
                <Input
                  placeholder="e.g., Shanghai Port"
                  value={formData.incoterms_place}
                  onChange={(e) => updateFormData("incoterms_place", e.target.value)}
                  className="bg-slate-800 border-slate-700 mt-1"
                />
              </div>
            </div>
            
            <div className="flex gap-8">
              <div className="flex items-center gap-3">
                <Switch
                  checked={formData.partial_shipments}
                  onCheckedChange={(v) => updateFormData("partial_shipments", v)}
                />
                <div>
                  <Label>Partial Shipments</Label>
                  <p className="text-xs text-slate-400">Allow multiple shipments</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Switch
                  checked={formData.transhipment}
                  onCheckedChange={(v) => updateFormData("transhipment", v)}
                />
                <div>
                  <Label>Transhipment</Label>
                  <p className="text-xs text-slate-400">Allow vessel changes</p>
                </div>
              </div>
            </div>
          </div>
        );
        
      case 4:
        return (
          <div className="space-y-6">
            <div>
              <Label>Description of Goods *</Label>
              <Textarea
                placeholder="Describe the goods in detail...&#10;&#10;Example:&#10;100% COTTON KNITWEAR&#10;- T-SHIRTS: 30,000 PCS&#10;- POLO SHIRTS: 12,000 PCS&#10;AS PER PROFORMA INVOICE NO. PI-2024-001"
                value={formData.goods_description}
                onChange={(e) => updateFormData("goods_description", e.target.value)}
                className="bg-slate-800 border-slate-700 mt-1 font-mono text-sm"
                rows={8}
              />
              <div className="mt-2 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <p className="text-xs text-amber-400 flex items-center gap-2">
                  <Info className="h-4 w-4" />
                  Tips for goods description:
                </p>
                <ul className="text-xs text-slate-400 mt-2 space-y-1 ml-6">
                  <li>• Be specific but not overly restrictive</li>
                  <li>• Include reference to Proforma Invoice/Contract</li>
                  <li>• Avoid brand names unless required</li>
                  <li>• Use clear quantities and units</li>
                </ul>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>HS Code (Optional)</Label>
                <Input
                  placeholder="e.g., 6109.10"
                  value={formData.hs_code}
                  onChange={(e) => updateFormData("hs_code", e.target.value)}
                  className="bg-slate-800 border-slate-700 mt-1"
                />
              </div>
              <div>
                <Label>Quantity</Label>
                <Input
                  placeholder="e.g., 50,000 PCS"
                  value={formData.quantity}
                  onChange={(e) => updateFormData("quantity", e.target.value)}
                  className="bg-slate-800 border-slate-700 mt-1"
                />
              </div>
              <div>
                <Label>Unit Price</Label>
                <Input
                  placeholder="e.g., USD 5.50/PC"
                  value={formData.unit_price}
                  onChange={(e) => updateFormData("unit_price", e.target.value)}
                  className="bg-slate-800 border-slate-700 mt-1"
                />
              </div>
            </div>
          </div>
        );
        
      case 5:
        return (
          <div className="space-y-6">
            <div>
              <Label className="text-base">Select Required Documents</Label>
              <p className="text-sm text-slate-400 mb-4">
                Check the documents you need the beneficiary to provide
              </p>
              
              <div className="space-y-3">
                {STANDARD_DOCUMENTS.map((doc) => {
                  const isSelected = formData.documents_required.some(
                    (d) => d.document_type === doc.type
                  );
                  const selectedDoc = formData.documents_required.find(
                    (d) => d.document_type === doc.type
                  );
                  
                  return (
                    <div
                      key={doc.type}
                      className={cn(
                        "p-4 rounded-lg border transition-colors",
                        isSelected
                          ? "bg-emerald-500/10 border-emerald-500/30"
                          : "bg-slate-800/50 border-slate-700"
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Checkbox
                            checked={isSelected}
                            onCheckedChange={(checked) =>
                              toggleDocument(doc.type, !!checked)
                            }
                          />
                          <span className="text-white">{doc.label}</span>
                        </div>
                        {isSelected && (
                          <div className="flex items-center gap-2">
                            <Input
                              type="number"
                              min="1"
                              max="10"
                              value={selectedDoc?.copies_original || 1}
                              onChange={(e) => {
                                const docs = formData.documents_required.map((d) =>
                                  d.document_type === doc.type
                                    ? { ...d, copies_original: parseInt(e.target.value) || 1 }
                                    : d
                                );
                                updateFormData("documents_required", docs);
                              }}
                              className="w-16 h-8 bg-slate-800 border-slate-600 text-center"
                            />
                            <span className="text-xs text-slate-400">original(s)</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        );
        
      case 6:
        return (
          <div className="space-y-6">
            <div>
              <Label>Payment Terms *</Label>
              <Select
                value={formData.payment_terms}
                onValueChange={(v) => updateFormData("payment_terms", v)}
              >
                <SelectTrigger className="bg-slate-800 border-slate-700 mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sight">At Sight (Immediate Payment)</SelectItem>
                  <SelectItem value="usance">Usance (Deferred Payment)</SelectItem>
                  <SelectItem value="deferred">Deferred Payment</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {formData.payment_terms === "usance" && (
              <div className="grid grid-cols-2 gap-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <div>
                  <Label>Days</Label>
                  <Select
                    value={formData.usance_days}
                    onValueChange={(v) => updateFormData("usance_days", v)}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-600 mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="30">30 Days</SelectItem>
                      <SelectItem value="60">60 Days</SelectItem>
                      <SelectItem value="90">90 Days</SelectItem>
                      <SelectItem value="120">120 Days</SelectItem>
                      <SelectItem value="180">180 Days</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>From</Label>
                  <Select
                    value={formData.usance_from}
                    onValueChange={(v) => updateFormData("usance_from", v)}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-600 mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="bl_date">B/L Date</SelectItem>
                      <SelectItem value="invoice_date">Invoice Date</SelectItem>
                      <SelectItem value="presentation">Presentation</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>LC Expiry Date *</Label>
                <Input
                  type="date"
                  value={formData.expiry_date}
                  onChange={(e) => updateFormData("expiry_date", e.target.value)}
                  className="bg-slate-800 border-slate-700 mt-1"
                />
                <p className="text-xs text-slate-400 mt-1">
                  Should be at least 21 days after latest shipment
                </p>
              </div>
              <div>
                <Label>Expiry Place</Label>
                <Input
                  placeholder="Beneficiary's country"
                  value={formData.expiry_place}
                  onChange={(e) => updateFormData("expiry_place", e.target.value)}
                  className="bg-slate-800 border-slate-700 mt-1"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Presentation Period</Label>
                <Select
                  value={formData.presentation_period}
                  onValueChange={(v) => updateFormData("presentation_period", v)}
                >
                  <SelectTrigger className="bg-slate-800 border-slate-700 mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="14">14 Days</SelectItem>
                    <SelectItem value="21">21 Days (UCP600 Default)</SelectItem>
                    <SelectItem value="30">30 Days</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Confirmation</Label>
                <Select
                  value={formData.confirmation_instructions}
                  onValueChange={(v) => updateFormData("confirmation_instructions", v)}
                >
                  <SelectTrigger className="bg-slate-800 border-slate-700 mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="without">Without (Cheaper)</SelectItem>
                    <SelectItem value="may_add">May Add (Bank's Option)</SelectItem>
                    <SelectItem value="confirm">Confirm (Extra Security)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        );
        
      default:
        return null;
    }
  };
  
  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" asChild>
                <Link to="/lc-builder/dashboard">
                  <ArrowLeft className="h-5 w-5" />
                </Link>
              </Button>
              <div>
                <h1 className="text-xl font-bold text-white">
                  {id ? "Edit LC Application" : "New LC Application"}
                </h1>
                <p className="text-sm text-slate-400">
                  Step {currentStep} of {STEPS.length}: {STEPS[currentStep - 1].title}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => handleSave(true)}
                disabled={saving}
              >
                <Save className="h-4 w-4 mr-2" />
                Save Draft
              </Button>
              {id && (
                <Button
                  variant="outline"
                  onClick={handlePreviewMT700}
                >
                  <Eye className="h-4 w-4 mr-2" />
                  MT700 Preview
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
      
      <div className="container mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-4 gap-6">
          {/* Step Navigation */}
          <div className="lg:col-span-1">
            <div className="sticky top-6 space-y-2">
              {STEPS.map((step) => (
                <button
                  key={step.id}
                  onClick={() => setCurrentStep(step.id)}
                  className={cn(
                    "w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors",
                    currentStep === step.id
                      ? "bg-emerald-500/10 border border-emerald-500/30"
                      : "bg-slate-900 border border-slate-800 hover:border-slate-700"
                  )}
                >
                  <div
                    className={cn(
                      "p-2 rounded-lg",
                      currentStep === step.id
                        ? "bg-emerald-500/20"
                        : "bg-slate-800"
                    )}
                  >
                    <step.icon
                      className={cn(
                        "h-4 w-4",
                        currentStep === step.id
                          ? "text-emerald-400"
                          : "text-slate-400"
                      )}
                    />
                  </div>
                  <div>
                    <p
                      className={cn(
                        "text-sm font-medium",
                        currentStep === step.id ? "text-white" : "text-slate-400"
                      )}
                    >
                      {step.title}
                    </p>
                    <p className="text-xs text-slate-500">{step.description}</p>
                  </div>
                </button>
              ))}
              
              {/* Validation Summary */}
              {validation && (
                <Card className="mt-4 bg-slate-900 border-slate-800">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Validation</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-400">Risk Score</span>
                        <Badge
                          variant={
                            validation.risk_score <= 20
                              ? "default"
                              : validation.risk_score <= 50
                              ? "secondary"
                              : "destructive"
                          }
                        >
                          {validation.risk_score}
                        </Badge>
                      </div>
                      {validation.issues?.length > 0 && (
                        <div className="pt-2 border-t border-slate-800">
                          <p className="text-xs text-slate-400 mb-2">
                            {validation.issues.length} issue(s)
                          </p>
                          {validation.issues.slice(0, 3).map((issue: any, i: number) => (
                            <div
                              key={i}
                              className="flex items-start gap-2 text-xs mb-1"
                            >
                              <AlertTriangle
                                className={cn(
                                  "h-3 w-3 mt-0.5 shrink-0",
                                  issue.severity === "error"
                                    ? "text-red-400"
                                    : issue.severity === "warning"
                                    ? "text-amber-400"
                                    : "text-blue-400"
                                )}
                              />
                              <span className="text-slate-400">{issue.message}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
          
          {/* Step Content */}
          <div className="lg:col-span-3">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {(() => {
                    const StepIcon = STEPS[currentStep - 1].icon;
                    return <StepIcon className="h-5 w-5 text-emerald-400" />;
                  })()}
                  {STEPS[currentStep - 1].title}
                </CardTitle>
                <CardDescription>
                  {STEPS[currentStep - 1].description}
                </CardDescription>
              </CardHeader>
              <CardContent>{renderStepContent()}</CardContent>
            </Card>
            
            {/* Navigation Buttons */}
            <div className="flex items-center justify-between mt-6">
              <Button
                variant="outline"
                onClick={() => setCurrentStep((s) => s - 1)}
                disabled={currentStep === 1}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Previous
              </Button>
              
              {currentStep < STEPS.length ? (
                <Button
                  className="bg-emerald-600 hover:bg-emerald-700"
                  onClick={() => setCurrentStep((s) => s + 1)}
                >
                  Next
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              ) : (
                <Button
                  className="bg-emerald-600 hover:bg-emerald-700"
                  onClick={() => handleSave(false)}
                  disabled={saving}
                >
                  <Check className="h-4 w-4 mr-2" />
                  Complete & Save
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* MT700 Preview Dialog */}
      <Dialog open={showMT700Dialog} onOpenChange={setShowMT700Dialog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>MT700 SWIFT Message Preview</DialogTitle>
          </DialogHeader>
          {mt700Preview && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <Badge variant={mt700Preview.is_valid ? "default" : "destructive"}>
                    {mt700Preview.is_valid ? "Valid" : "Has Issues"}
                  </Badge>
                  <span className="text-sm text-slate-400">
                    {mt700Preview.character_count} characters
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(mt700Preview.message);
                    toast({ title: "Copied", description: "MT700 message copied to clipboard" });
                  }}
                >
                  Copy
                </Button>
              </div>
              
              <pre className="p-4 bg-slate-900 rounded-lg text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">
                {mt700Preview.message}
              </pre>
              
              {mt700Preview.validation_errors?.length > 0 && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <p className="text-sm font-medium text-red-400 mb-2">Validation Issues:</p>
                  <ul className="space-y-1">
                    {mt700Preview.validation_errors.map((err: string, i: number) => (
                      <li key={i} className="text-xs text-red-300 flex items-center gap-2">
                        <AlertTriangle className="h-3 w-3" />
                        {err}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

