/**
 * Bank Formats Page
 * 
 * View and select bank-specific document format requirements
 */

import { useState, useEffect } from "react";
import {
  Building2,
  Loader2,
  Search,
  CheckCircle,
  AlertTriangle,
  Info,
  Globe,
  FileText,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface Bank {
  code: string;
  name: string;
  country: string;
  swift: string;
}

interface BankProfile {
  code: string;
  name: string;
  country: string;
  swift: string;
  general_requirements: string[];
  document_formats: Record<string, {
    fields: Array<{
      field_name: string;
      required: boolean;
      format: string | null;
      notes: string | null;
    }>;
    certification_text: string | null;
    special_instructions: string | null;
  }>;
}

export function BankFormatsPage() {
  const { toast } = useToast();
  const { session } = useAuth();
  
  const [banks, setBanks] = useState<Bank[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedBank, setSelectedBank] = useState<BankProfile | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [countryFilter, setCountryFilter] = useState<string>("");

  useEffect(() => {
    fetchBanks();
  }, []);

  const fetchBanks = async () => {
    try {
      const response = await fetch(`${API_BASE}/doc-generator/advanced/banks`, {
        headers: { Authorization: `Bearer ${session?.access_token || ""}` },
      });
      if (response.ok) {
        const data = await response.json();
        setBanks(data.banks);
      }
    } catch (error) {
      console.error("Error fetching banks:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBankProfile = async (code: string) => {
    setLoadingProfile(true);
    try {
      const response = await fetch(`${API_BASE}/doc-generator/advanced/banks/${code}`, {
        headers: { Authorization: `Bearer ${session?.access_token || ""}` },
      });
      if (response.ok) {
        setSelectedBank(await response.json());
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to load bank profile", variant: "destructive" });
    } finally {
      setLoadingProfile(false);
    }
  };

  const countries = [...new Set(banks.map(b => b.country))].sort();

  const filteredBanks = banks.filter(b => {
    const matchesSearch = 
      b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.swift.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCountry = !countryFilter || b.country === countryFilter;
    return matchesSearch && matchesCountry;
  });

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Bank-Specific Formats</h1>
        <p className="text-slate-400">
          View document requirements for different banks
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Bank List */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="bg-slate-900/50 border-slate-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-white text-lg">Banks</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Filters */}
              <div className="space-y-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search banks..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 bg-slate-800 border-slate-700"
                  />
                </div>
                <Select value={countryFilter || "all"} onValueChange={(v) => setCountryFilter(v === "all" ? "" : v)}>
                  <SelectTrigger className="bg-slate-800 border-slate-700">
                    <SelectValue placeholder="All Countries" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Countries</SelectItem>
                    {countries.map((country) => (
                      <SelectItem key={country} value={country}>{country}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Bank List */}
              {loading ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
                </div>
              ) : (
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {filteredBanks.map((bank) => (
                    <button
                      key={bank.code}
                      onClick={() => fetchBankProfile(bank.code)}
                      className={`w-full text-left p-3 rounded-lg transition-colors ${
                        selectedBank?.code === bank.code
                          ? 'bg-blue-600/20 border border-blue-500'
                          : 'bg-slate-800/50 hover:bg-slate-800 border border-transparent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-white">{bank.name}</div>
                          <div className="text-xs text-slate-400">
                            {bank.code} • {bank.country}
                          </div>
                        </div>
                        {bank.swift && (
                          <Badge variant="outline" className="text-xs">
                            {bank.swift}
                          </Badge>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Bank Details */}
        <div className="lg:col-span-2">
          {loadingProfile ? (
            <Card className="bg-slate-900/50 border-slate-800">
              <CardContent className="flex items-center justify-center p-12">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
              </CardContent>
            </Card>
          ) : selectedBank ? (
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-white flex items-center gap-2">
                      <Building2 className="h-5 w-5" />
                      {selectedBank.name}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      <span className="flex items-center gap-2">
                        <Globe className="h-3 w-3" />
                        {selectedBank.country}
                        {selectedBank.swift && (
                          <>
                            <span className="text-slate-600">•</span>
                            <span className="font-mono">{selectedBank.swift}</span>
                          </>
                        )}
                      </span>
                    </CardDescription>
                  </div>
                  <Badge>{selectedBank.code}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* General Requirements */}
                {selectedBank.general_requirements.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="font-medium text-white flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      General Requirements
                    </h3>
                    <ul className="space-y-2">
                      {selectedBank.general_requirements.map((req, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                          <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                          {req}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Document Formats */}
                <div className="space-y-3">
                  <h3 className="font-medium text-white flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Document Format Requirements
                  </h3>
                  
                  <Accordion type="single" collapsible className="w-full">
                    {Object.entries(selectedBank.document_formats).map(([docType, format]) => (
                      <AccordionItem key={docType} value={docType} className="border-slate-800">
                        <AccordionTrigger className="text-white hover:no-underline">
                          <span className="flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            {docType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            <Badge variant="outline" className="ml-2">
                              {format.fields.length} fields
                            </Badge>
                          </span>
                        </AccordionTrigger>
                        <AccordionContent className="space-y-4">
                          {/* Fields */}
                          {format.fields.length > 0 && (
                            <div className="space-y-2">
                              <h4 className="text-sm font-medium text-slate-300">Required Fields:</h4>
                              {format.fields.map((field, i) => (
                                <div key={i} className="p-3 bg-slate-800/50 rounded-lg">
                                  <div className="flex items-center justify-between">
                                    <span className="font-mono text-sm text-white">
                                      {field.field_name}
                                    </span>
                                    <Badge variant={field.required ? "destructive" : "outline"}>
                                      {field.required ? "Required" : "Optional"}
                                    </Badge>
                                  </div>
                                  {field.notes && (
                                    <p className="text-xs text-slate-400 mt-1">{field.notes}</p>
                                  )}
                                  {field.format && (
                                    <p className="text-xs text-slate-500 mt-1 font-mono">
                                      Format: {field.format}
                                    </p>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Certification Text */}
                          {format.certification_text && (
                            <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                              <h4 className="text-sm font-medium text-blue-300 mb-1">
                                Required Certification Text:
                              </h4>
                              <p className="text-sm text-blue-200 italic">
                                "{format.certification_text}"
                              </p>
                            </div>
                          )}

                          {/* Special Instructions */}
                          {format.special_instructions && (
                            <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                              <div className="flex items-start gap-2">
                                <Info className="h-4 w-4 text-amber-500 mt-0.5" />
                                <p className="text-sm text-amber-200">
                                  {format.special_instructions}
                                </p>
                              </div>
                            </div>
                          )}
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-slate-900/50 border-slate-800">
              <CardContent className="flex flex-col items-center justify-center p-12 text-center">
                <Building2 className="h-12 w-12 text-slate-600 mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">Select a Bank</h3>
                <p className="text-slate-400">
                  Choose a bank from the list to view their specific document requirements
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

export default BankFormatsPage;

