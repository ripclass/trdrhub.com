/**
 * Create Document Wizard
 * 
 * Step-by-step wizard to create a new document set:
 * 1. LC Details
 * 2. Shipment & Goods
 * 3. Select & Generate Documents
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Ship,
  Package,
  ArrowLeft,
  ArrowRight,
  Plus,
  Trash2,
  CheckCircle,
  Download,
  Eye,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface LineItem {
  line_number: number;
  description: string;
  hs_code: string;
  quantity: number;
  unit: string;
  unit_price: number;
  cartons: number;
  gross_weight_kg: number;
  net_weight_kg: number;
}

interface FormData {
  // LC Details
  name: string;
  lc_number: string;
  lc_date: string;
  lc_currency: string;
  issuing_bank: string;
  
  // Parties
  beneficiary_name: string;
  beneficiary_address: string;
  beneficiary_country: string;
  applicant_name: string;
  applicant_address: string;
  applicant_country: string;
  notify_party_name: string;
  notify_party_address: string;
  
  // Shipment
  vessel_name: string;
  voyage_number: string;
  bl_number: string;
  bl_date: string;
  container_number: string;
  seal_number: string;
  port_of_loading: string;
  port_of_discharge: string;
  incoterms: string;
  incoterms_place: string;
  
  // Packing
  total_cartons: number;
  gross_weight_kg: number;
  net_weight_kg: number;
  cbm: number;
  shipping_marks: string;
  
  // Document Numbers
  invoice_number: string;
  invoice_date: string;
  country_of_origin: string;
  
  // Bill of Exchange
  draft_tenor: string;
  drawee_name: string;
  
  // Line Items
  line_items: LineItem[];
}

const defaultFormData: FormData = {
  name: "",
  lc_number: "",
  lc_date: "",
  lc_currency: "USD",
  issuing_bank: "",
  beneficiary_name: "",
  beneficiary_address: "",
  beneficiary_country: "",
  applicant_name: "",
  applicant_address: "",
  applicant_country: "",
  notify_party_name: "",
  notify_party_address: "",
  vessel_name: "",
  voyage_number: "",
  bl_number: "",
  bl_date: "",
  container_number: "",
  seal_number: "",
  port_of_loading: "",
  port_of_discharge: "",
  incoterms: "FOB",
  incoterms_place: "",
  total_cartons: 0,
  gross_weight_kg: 0,
  net_weight_kg: 0,
  cbm: 0,
  shipping_marks: "",
  invoice_number: "",
  invoice_date: new Date().toISOString().split("T")[0],
  country_of_origin: "",
  draft_tenor: "AT SIGHT",
  drawee_name: "",
  line_items: [],
};

const defaultLineItem: LineItem = {
  line_number: 1,
  description: "",
  hs_code: "",
  quantity: 0,
  unit: "PCS",
  unit_price: 0,
  cartons: 0,
  gross_weight_kg: 0,
  net_weight_kg: 0,
};

const STEPS = [
  { id: 1, title: "LC Details", icon: FileText },
  { id: 2, title: "Shipment & Goods", icon: Ship },
  { id: 3, title: "Generate", icon: Package },
];

const INCOTERMS = ["FOB", "CIF", "CFR", "EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP"];
const TENORS = ["AT SIGHT", "30 DAYS", "60 DAYS", "90 DAYS", "120 DAYS", "180 DAYS"];
const UNITS = ["PCS", "KG", "MT", "MTR", "YDS", "SET", "DOZ", "CTN", "PKG", "UNIT"];
const CURRENCIES = ["USD", "EUR", "GBP", "BDT", "INR", "PKR", "CNY", "JPY"];

export default function CreateDocumentWizard() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user, session } = useAuth();
  
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<FormData>(defaultFormData);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdSetId, setCreatedSetId] = useState<string | null>(null);
  const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>([
    "commercial_invoice",
    "packing_list",
  ]);

  const updateField = (field: keyof FormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const addLineItem = () => {
    const newItem = {
      ...defaultLineItem,
      line_number: formData.line_items.length + 1,
    };
    setFormData((prev) => ({
      ...prev,
      line_items: [...prev.line_items, newItem],
    }));
  };

  const removeLineItem = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      line_items: prev.line_items.filter((_, i) => i !== index).map((item, i) => ({
        ...item,
        line_number: i + 1,
      })),
    }));
  };

  const updateLineItem = (index: number, field: keyof LineItem, value: any) => {
    setFormData((prev) => ({
      ...prev,
      line_items: prev.line_items.map((item, i) =>
        i === index ? { ...item, [field]: value } : item
      ),
    }));
  };

  const calculateTotals = () => {
    const totalQty = formData.line_items.reduce((sum, item) => sum + (item.quantity || 0), 0);
    const totalAmount = formData.line_items.reduce(
      (sum, item) => sum + (item.quantity || 0) * (item.unit_price || 0),
      0
    );
    const totalCartons = formData.line_items.reduce((sum, item) => sum + (item.cartons || 0), 0);
    const totalGross = formData.line_items.reduce((sum, item) => sum + (item.gross_weight_kg || 0), 0);
    const totalNet = formData.line_items.reduce((sum, item) => sum + (item.net_weight_kg || 0), 0);
    
    return { totalQty, totalAmount, totalCartons, totalGross, totalNet };
  };

  const handleCreateAndGenerate = async () => {
    if (formData.line_items.length === 0) {
      toast({
        title: "Error",
        description: "Please add at least one line item",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    
    try {
      const token = session?.access_token || user?.id;
      
      // Create document set
      const createResponse = await fetch(`${API_BASE}/doc-generator/document-sets`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...formData,
          lc_date: formData.lc_date || null,
          bl_date: formData.bl_date || null,
          invoice_date: formData.invoice_date || null,
          lc_amount: calculateTotals().totalAmount,
        }),
      });
      
      if (!createResponse.ok) {
        throw new Error("Failed to create document set");
      }
      
      const createdSet = await createResponse.json();
      setCreatedSetId(createdSet.id);
      
      // Generate documents
      const generateResponse = await fetch(
        `${API_BASE}/doc-generator/document-sets/${createdSet.id}/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            document_types: selectedDocTypes,
          }),
        }
      );
      
      if (!generateResponse.ok) {
        throw new Error("Failed to generate documents");
      }
      
      toast({
        title: "Success!",
        description: "Documents have been generated",
      });
      
      setStep(4); // Move to success step
    } catch (error) {
      console.error("Error:", error);
      toast({
        title: "Error",
        description: "Failed to create document set",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownload = async () => {
    if (!createdSetId) return;
    
    try {
      const token = session?.access_token || user?.id;
      const response = await fetch(
        `${API_BASE}/doc-generator/document-sets/${createdSetId}/download`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      
      if (!response.ok) throw new Error("Download failed");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `documents_${formData.lc_number || "set"}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to download documents",
        variant: "destructive",
      });
    }
  };

  const { totalQty, totalAmount, totalCartons, totalGross, totalNet } = calculateTotals();

  return (
    <div className="p-6">
      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-center gap-4">
          {STEPS.map((s, index) => {
            const isActive = step === s.id;
            const isCompleted = step > s.id;
            const Icon = s.icon;
            
            return (
              <div key={s.id} className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      isCompleted
                        ? "bg-green-600 text-white"
                        : isActive
                        ? "bg-blue-600 text-white"
                        : "bg-slate-700 text-slate-400"
                    }`}
                  >
                    {isCompleted ? <CheckCircle className="w-5 h-5" /> : <Icon className="w-5 h-5" />}
                  </div>
                  <span
                    className={`text-sm font-medium ${
                      isActive ? "text-white" : "text-slate-400"
                    }`}
                  >
                    {s.title}
                  </span>
                </div>
                {index < STEPS.length - 1 && (
                  <div className={`w-16 h-0.5 ${isCompleted ? "bg-green-600" : "bg-slate-700"}`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Step 1: LC Details */}
      {step === 1 && (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white">LC & Party Details</CardTitle>
            <CardDescription className="text-slate-400">
              Enter the Letter of Credit and party information
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* LC Reference */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label className="text-slate-300">LC Number</Label>
                <Input
                  value={formData.lc_number}
                  onChange={(e) => updateField("lc_number", e.target.value)}
                  placeholder="e.g., EXP2024112900001"
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-slate-300">LC Date</Label>
                <Input
                  type="date"
                  value={formData.lc_date}
                  onChange={(e) => updateField("lc_date", e.target.value)}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-slate-300">Currency</Label>
                <Select value={formData.lc_currency} onValueChange={(v) => updateField("lc_currency", v)}>
                  <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map((c) => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Separator className="bg-slate-800" />

            {/* Beneficiary */}
            <div>
              <h3 className="text-lg font-medium text-white mb-4">Beneficiary (Seller)</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-slate-300">Company Name *</Label>
                  <Input
                    value={formData.beneficiary_name}
                    onChange={(e) => updateField("beneficiary_name", e.target.value)}
                    placeholder="Your company name"
                    className="bg-slate-800 border-slate-700 text-white"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-slate-300">Country</Label>
                  <Input
                    value={formData.beneficiary_country}
                    onChange={(e) => updateField("beneficiary_country", e.target.value)}
                    placeholder="e.g., Bangladesh"
                    className="bg-slate-800 border-slate-700 text-white"
                  />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label className="text-slate-300">Address</Label>
                  <Textarea
                    value={formData.beneficiary_address}
                    onChange={(e) => updateField("beneficiary_address", e.target.value)}
                    placeholder="Full address"
                    className="bg-slate-800 border-slate-700 text-white"
                    rows={2}
                  />
                </div>
              </div>
            </div>

            <Separator className="bg-slate-800" />

            {/* Applicant */}
            <div>
              <h3 className="text-lg font-medium text-white mb-4">Applicant (Buyer)</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-slate-300">Company Name *</Label>
                  <Input
                    value={formData.applicant_name}
                    onChange={(e) => updateField("applicant_name", e.target.value)}
                    placeholder="Buyer company name"
                    className="bg-slate-800 border-slate-700 text-white"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-slate-300">Country</Label>
                  <Input
                    value={formData.applicant_country}
                    onChange={(e) => updateField("applicant_country", e.target.value)}
                    placeholder="e.g., China"
                    className="bg-slate-800 border-slate-700 text-white"
                  />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label className="text-slate-300">Address</Label>
                  <Textarea
                    value={formData.applicant_address}
                    onChange={(e) => updateField("applicant_address", e.target.value)}
                    placeholder="Full address"
                    className="bg-slate-800 border-slate-700 text-white"
                    rows={2}
                  />
                </div>
              </div>
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-4">
              <Button
                variant="outline"
                onClick={() => navigate("/doc-generator/dashboard")}
                className="border-slate-700 text-slate-300"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Cancel
              </Button>
              <Button
                onClick={() => setStep(2)}
                disabled={!formData.beneficiary_name || !formData.applicant_name}
                className="bg-blue-600 hover:bg-blue-700"
              >
                Next: Shipment Details
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Shipment & Goods */}
      {step === 2 && (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white">Shipment & Goods</CardTitle>
            <CardDescription className="text-slate-400">
              Enter shipping details and line items
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Shipping Details */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label className="text-slate-300">Vessel Name</Label>
                <Input
                  value={formData.vessel_name}
                  onChange={(e) => updateField("vessel_name", e.target.value)}
                  placeholder="e.g., MAERSK INFINITY"
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-slate-300">B/L Number</Label>
                <Input
                  value={formData.bl_number}
                  onChange={(e) => updateField("bl_number", e.target.value)}
                  placeholder="e.g., MSKU7788990123"
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-slate-300">B/L Date</Label>
                <Input
                  type="date"
                  value={formData.bl_date}
                  onChange={(e) => updateField("bl_date", e.target.value)}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-slate-300">Port of Loading</Label>
                <Input
                  value={formData.port_of_loading}
                  onChange={(e) => updateField("port_of_loading", e.target.value)}
                  placeholder="e.g., Chittagong, Bangladesh"
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-slate-300">Port of Discharge</Label>
                <Input
                  value={formData.port_of_discharge}
                  onChange={(e) => updateField("port_of_discharge", e.target.value)}
                  placeholder="e.g., Shanghai, China"
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-slate-300">Incoterms</Label>
                <Select value={formData.incoterms} onValueChange={(v) => updateField("incoterms", v)}>
                  <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {INCOTERMS.map((t) => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Separator className="bg-slate-800" />

            {/* Line Items */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-white">Line Items (Goods)</h3>
                <Button onClick={addLineItem} className="bg-blue-600 hover:bg-blue-700">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Item
                </Button>
              </div>

              {formData.line_items.length === 0 ? (
                <div className="text-center py-8 border border-dashed border-slate-700 rounded-lg">
                  <Package className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <p className="text-slate-400 mb-4">No line items yet</p>
                  <Button onClick={addLineItem} variant="outline" className="border-slate-700">
                    <Plus className="w-4 h-4 mr-2" />
                    Add First Item
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {formData.line_items.map((item, index) => (
                    <div key={index} className="p-4 border border-slate-700 rounded-lg space-y-4">
                      <div className="flex items-center justify-between">
                        <Badge variant="secondary">Line {item.line_number}</Badge>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeLineItem(index)}
                          className="text-red-400 hover:text-red-300"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="space-y-2 md:col-span-2">
                          <Label className="text-slate-300">Description *</Label>
                          <Input
                            value={item.description}
                            onChange={(e) => updateLineItem(index, "description", e.target.value)}
                            placeholder="e.g., 100% Cotton T-Shirts M/L/XL"
                            className="bg-slate-800 border-slate-700 text-white"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-slate-300">HS Code</Label>
                          <Input
                            value={item.hs_code}
                            onChange={(e) => updateLineItem(index, "hs_code", e.target.value)}
                            placeholder="e.g., 6109.10"
                            className="bg-slate-800 border-slate-700 text-white"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-slate-300">Quantity *</Label>
                          <Input
                            type="number"
                            value={item.quantity || ""}
                            onChange={(e) => updateLineItem(index, "quantity", parseInt(e.target.value) || 0)}
                            className="bg-slate-800 border-slate-700 text-white"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-slate-300">Unit</Label>
                          <Select
                            value={item.unit}
                            onValueChange={(v) => updateLineItem(index, "unit", v)}
                          >
                            <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {UNITS.map((u) => (
                                <SelectItem key={u} value={u}>{u}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label className="text-slate-300">Unit Price ($)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.unit_price || ""}
                            onChange={(e) => updateLineItem(index, "unit_price", parseFloat(e.target.value) || 0)}
                            className="bg-slate-800 border-slate-700 text-white"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-slate-300">Cartons</Label>
                          <Input
                            type="number"
                            value={item.cartons || ""}
                            onChange={(e) => updateLineItem(index, "cartons", parseInt(e.target.value) || 0)}
                            className="bg-slate-800 border-slate-700 text-white"
                          />
                        </div>
                        <div className="flex items-center text-slate-300 font-medium pt-6">
                          = ${((item.quantity || 0) * (item.unit_price || 0)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Totals */}
                  <div className="p-4 bg-slate-800/50 rounded-lg">
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
                      <div>
                        <p className="text-slate-400 text-sm">Total Qty</p>
                        <p className="text-white font-bold">{totalQty.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-slate-400 text-sm">Total Amount</p>
                        <p className="text-white font-bold">${totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
                      </div>
                      <div>
                        <p className="text-slate-400 text-sm">Total Cartons</p>
                        <p className="text-white font-bold">{totalCartons.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-slate-400 text-sm">Gross Wt (KG)</p>
                        <p className="text-white font-bold">{totalGross.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-slate-400 text-sm">Net Wt (KG)</p>
                        <p className="text-white font-bold">{totalNet.toLocaleString()}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <Separator className="bg-slate-800" />

            {/* Document Info */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label className="text-slate-300">Invoice Number</Label>
                <Input
                  value={formData.invoice_number}
                  onChange={(e) => updateField("invoice_number", e.target.value)}
                  placeholder="e.g., INV-2024-001"
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-slate-300">Invoice Date</Label>
                <Input
                  type="date"
                  value={formData.invoice_date}
                  onChange={(e) => updateField("invoice_date", e.target.value)}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-slate-300">Country of Origin</Label>
                <Input
                  value={formData.country_of_origin}
                  onChange={(e) => updateField("country_of_origin", e.target.value)}
                  placeholder="e.g., Bangladesh"
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Shipping Marks</Label>
              <Textarea
                value={formData.shipping_marks}
                onChange={(e) => updateField("shipping_marks", e.target.value)}
                placeholder="e.g., SHANGHAI FASHION / MADE IN BANGLADESH / CARTON NO. 1-1850"
                className="bg-slate-800 border-slate-700 text-white"
                rows={3}
              />
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-4">
              <Button
                variant="outline"
                onClick={() => setStep(1)}
                className="border-slate-700 text-slate-300"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <Button
                onClick={() => setStep(3)}
                disabled={formData.line_items.length === 0}
                className="bg-blue-600 hover:bg-blue-700"
              >
                Next: Generate Documents
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Generate */}
      {step === 3 && (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white">Select & Generate Documents</CardTitle>
            <CardDescription className="text-slate-400">
              Choose which documents to generate
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Document Selection */}
            <div className="space-y-4">
              <div className="flex items-center space-x-3 p-4 border border-slate-700 rounded-lg">
                <Checkbox
                  checked={selectedDocTypes.includes("commercial_invoice")}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedDocTypes([...selectedDocTypes, "commercial_invoice"]);
                    } else {
                      setSelectedDocTypes(selectedDocTypes.filter((t) => t !== "commercial_invoice"));
                    }
                  }}
                />
                <div className="flex-1">
                  <p className="text-white font-medium">Commercial Invoice</p>
                  <p className="text-slate-400 text-sm">Primary trade document with goods, amounts, and parties</p>
                </div>
                <Badge variant="default">Required</Badge>
              </div>

              <div className="flex items-center space-x-3 p-4 border border-slate-700 rounded-lg">
                <Checkbox
                  checked={selectedDocTypes.includes("packing_list")}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedDocTypes([...selectedDocTypes, "packing_list"]);
                    } else {
                      setSelectedDocTypes(selectedDocTypes.filter((t) => t !== "packing_list"));
                    }
                  }}
                />
                <div className="flex-1">
                  <p className="text-white font-medium">Packing List</p>
                  <p className="text-slate-400 text-sm">Detailed breakdown of cartons, weights, and packaging</p>
                </div>
                <Badge variant="secondary">Recommended</Badge>
              </div>

              <div className="flex items-center space-x-3 p-4 border border-slate-700 rounded-lg">
                <Checkbox
                  checked={selectedDocTypes.includes("beneficiary_certificate")}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedDocTypes([...selectedDocTypes, "beneficiary_certificate"]);
                    } else {
                      setSelectedDocTypes(selectedDocTypes.filter((t) => t !== "beneficiary_certificate"));
                    }
                  }}
                />
                <div className="flex-1">
                  <p className="text-white font-medium">Beneficiary Certificate</p>
                  <p className="text-slate-400 text-sm">Certification of LC compliance by beneficiary</p>
                </div>
                <Badge variant="secondary">Optional</Badge>
              </div>

              <div className="flex items-center space-x-3 p-4 border border-slate-700 rounded-lg">
                <Checkbox
                  checked={selectedDocTypes.includes("bill_of_exchange")}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedDocTypes([...selectedDocTypes, "bill_of_exchange"]);
                    } else {
                      setSelectedDocTypes(selectedDocTypes.filter((t) => t !== "bill_of_exchange"));
                    }
                  }}
                />
                <div className="flex-1">
                  <p className="text-white font-medium">Bill of Exchange (Draft)</p>
                  <p className="text-slate-400 text-sm">Payment instruction to the issuing bank</p>
                </div>
                <Badge variant="secondary">Optional</Badge>
              </div>
            </div>

            <Separator className="bg-slate-800" />

            {/* Summary */}
            <div className="p-4 bg-slate-800/50 rounded-lg space-y-2">
              <h4 className="text-white font-medium">Summary</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-slate-400">LC Number:</span>{" "}
                  <span className="text-white">{formData.lc_number || "-"}</span>
                </div>
                <div>
                  <span className="text-slate-400">Total Amount:</span>{" "}
                  <span className="text-white">{formData.lc_currency} {totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
                <div>
                  <span className="text-slate-400">Beneficiary:</span>{" "}
                  <span className="text-white">{formData.beneficiary_name}</span>
                </div>
                <div>
                  <span className="text-slate-400">Applicant:</span>{" "}
                  <span className="text-white">{formData.applicant_name}</span>
                </div>
                <div>
                  <span className="text-slate-400">Line Items:</span>{" "}
                  <span className="text-white">{formData.line_items.length}</span>
                </div>
                <div>
                  <span className="text-slate-400">Documents:</span>{" "}
                  <span className="text-white">{selectedDocTypes.length} selected</span>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-4">
              <Button
                variant="outline"
                onClick={() => setStep(2)}
                className="border-slate-700 text-slate-300"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <Button
                onClick={handleCreateAndGenerate}
                disabled={isSubmitting || selectedDocTypes.length === 0}
                className="bg-green-600 hover:bg-green-700"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Generate Documents
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Success */}
      {step === 4 && (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="text-center py-12">
            <div className="w-16 h-16 bg-green-600/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-8 h-8 text-green-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Documents Generated!</h2>
            <p className="text-slate-400 mb-8">
              Your shipping documents have been created successfully.
            </p>
            <div className="flex justify-center gap-4">
              <Button onClick={handleDownload} className="bg-blue-600 hover:bg-blue-700">
                <Download className="w-4 h-4 mr-2" />
                Download All (ZIP)
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate("/doc-generator/dashboard")}
                className="border-slate-700 text-slate-300"
              >
                View All Documents
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

