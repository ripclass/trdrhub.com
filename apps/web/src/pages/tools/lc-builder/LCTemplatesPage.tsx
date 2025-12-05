/**
 * LC Templates Page
 * 
 * Pre-configured LC templates for common trade scenarios.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Search,
  FileText,
  Ship,
  Shirt,
  Cpu,
  Wheat,
  Factory,
  Package,
  Plus,
  Clock,
  Globe,
  ArrowRight,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface LCTemplate {
  id: string;
  name: string;
  description: string;
  industry: string;
  trade_route: string;
  payment_terms: string;
  typical_documents: string[];
  usage_count: number;
}

const industryIcons: Record<string, React.ElementType> = {
  textiles: Shirt,
  electronics: Cpu,
  food: Wheat,
  machinery: Factory,
  general: Package,
};

// Pre-defined templates (will be replaced by API data)
const defaultTemplates: LCTemplate[] = [
  {
    id: "tpl-rmg-bd-us",
    name: "Bangladesh RMG to USA",
    description: "Standard LC for ready-made garments export from Bangladesh to United States",
    industry: "textiles",
    trade_route: "Bangladesh → USA",
    payment_terms: "At Sight",
    typical_documents: ["Commercial Invoice", "Packing List", "B/L", "GSP Form A", "Certificate of Origin"],
    usage_count: 1250,
  },
  {
    id: "tpl-rmg-bd-eu",
    name: "Bangladesh RMG to EU",
    description: "RMG export to European Union with GSP origin certificate",
    industry: "textiles",
    trade_route: "Bangladesh → EU",
    payment_terms: "At Sight",
    typical_documents: ["Commercial Invoice", "Packing List", "B/L", "EUR.1", "Certificate of Origin"],
    usage_count: 980,
  },
  {
    id: "tpl-elec-cn-us",
    name: "China Electronics to USA",
    description: "Electronics/electrical products from China to United States",
    industry: "electronics",
    trade_route: "China → USA",
    payment_terms: "60 Days Sight",
    typical_documents: ["Commercial Invoice", "Packing List", "B/L", "CE Certificate", "FCC Declaration"],
    usage_count: 850,
  },
  {
    id: "tpl-elec-cn-eu",
    name: "China Electronics to EU",
    description: "Electronics export to EU with CE marking and RoHS compliance",
    industry: "electronics",
    trade_route: "China → EU",
    payment_terms: "60 Days Sight",
    typical_documents: ["Commercial Invoice", "Packing List", "B/L", "CE Certificate", "RoHS Certificate"],
    usage_count: 720,
  },
  {
    id: "tpl-food-in-me",
    name: "India Food to Middle East",
    description: "Food products export from India to GCC countries with Halal certification",
    industry: "food",
    trade_route: "India → GCC",
    payment_terms: "At Sight",
    typical_documents: ["Commercial Invoice", "Packing List", "B/L", "Halal Certificate", "Health Certificate"],
    usage_count: 650,
  },
  {
    id: "tpl-mach-de-in",
    name: "Germany Machinery to India",
    description: "Industrial machinery export from Germany to India",
    industry: "machinery",
    trade_route: "Germany → India",
    payment_terms: "90 Days Sight",
    typical_documents: ["Commercial Invoice", "Packing List", "B/L", "Performance Certificate", "Warranty"],
    usage_count: 420,
  },
  {
    id: "tpl-textile-pk-uk",
    name: "Pakistan Textiles to UK",
    description: "Textile products from Pakistan to United Kingdom",
    industry: "textiles",
    trade_route: "Pakistan → UK",
    payment_terms: "At Sight",
    typical_documents: ["Commercial Invoice", "Packing List", "B/L", "Certificate of Origin", "GSP Form A"],
    usage_count: 380,
  },
  {
    id: "tpl-general-import",
    name: "General Import LC",
    description: "Standard import LC template for any goods",
    industry: "general",
    trade_route: "Any → Any",
    payment_terms: "At Sight",
    typical_documents: ["Commercial Invoice", "Packing List", "B/L", "Certificate of Origin"],
    usage_count: 5200,
  },
];

export default function LCTemplatesPage() {
  const navigate = useNavigate();
  const { session } = useAuth();
  const { toast } = useToast();
  
  const [templates, setTemplates] = useState<LCTemplate[]>(defaultTemplates);
  const [filteredTemplates, setFilteredTemplates] = useState<LCTemplate[]>(defaultTemplates);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [industryFilter, setIndustryFilter] = useState("all");

  useEffect(() => {
    // Could fetch from API if available
    // fetchTemplates();
  }, [session?.access_token]);

  useEffect(() => {
    filterTemplates();
  }, [templates, searchQuery, industryFilter]);

  const filterTemplates = () => {
    let filtered = [...templates];
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query) ||
          t.trade_route.toLowerCase().includes(query)
      );
    }
    
    if (industryFilter !== "all") {
      filtered = filtered.filter((t) => t.industry === industryFilter);
    }
    
    setFilteredTemplates(filtered);
  };

  const useTemplate = (template: LCTemplate) => {
    // Navigate to wizard with template pre-filled
    toast({
      title: "Template Selected",
      description: `Starting LC application with ${template.name} template`,
    });
    navigate("/lc-builder/dashboard/new", { state: { template } });
  };

  const industries = [...new Set(templates.map((t) => t.industry))];

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <FileText className="h-5 w-5 text-emerald-400" />
                LC Templates
              </h1>
              <p className="text-sm text-slate-400">
                Pre-configured templates for common trade scenarios
              </p>
            </div>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700"
              onClick={() => navigate("/lc-builder/dashboard/new")}
            >
              <Plus className="h-4 w-4 mr-2" />
              Start from Scratch
            </Button>
          </div>
        </div>
      </div>

      {/* Industry Filter */}
      <div className="px-6 py-4 border-b border-slate-800">
        <div className="flex flex-wrap gap-2">
          <Button
            variant={industryFilter === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setIndustryFilter("all")}
            className={industryFilter === "all" ? "bg-emerald-600" : ""}
          >
            All Industries
          </Button>
          {industries.map((industry) => {
            const Icon = industryIcons[industry] || Package;
            return (
              <Button
                key={industry}
                variant={industryFilter === industry ? "default" : "outline"}
                size="sm"
                onClick={() => setIndustryFilter(industry)}
                className={industryFilter === industry ? "bg-emerald-600" : ""}
              >
                <Icon className="h-4 w-4 mr-2" />
                {industry.charAt(0).toUpperCase() + industry.slice(1)}
              </Button>
            );
          })}
        </div>
      </div>

      {/* Search */}
      <div className="px-6 py-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-slate-800 border-slate-700"
          />
        </div>
      </div>

      {/* Templates Grid */}
      <div className="px-6 py-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredTemplates.map((template) => {
            const Icon = industryIcons[template.industry] || Package;
            
            return (
              <Card
                key={template.id}
                className="bg-slate-800/50 border-slate-700 hover:border-slate-600 transition-all cursor-pointer"
                onClick={() => useTemplate(template)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className={`p-2 rounded-lg bg-emerald-500/10`}>
                      <Icon className="h-5 w-5 text-emerald-400" />
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {template.usage_count.toLocaleString()} uses
                    </Badge>
                  </div>
                  <CardTitle className="text-lg text-white mt-2">
                    {template.name}
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    {template.description}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {/* Trade Route */}
                    <div className="flex items-center gap-2 text-sm">
                      <Globe className="h-4 w-4 text-slate-500" />
                      <span className="text-slate-300">{template.trade_route}</span>
                    </div>
                    
                    {/* Payment Terms */}
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="h-4 w-4 text-slate-500" />
                      <span className="text-slate-300">{template.payment_terms}</span>
                    </div>
                    
                    {/* Documents */}
                    <div className="flex flex-wrap gap-1">
                      {template.typical_documents.slice(0, 3).map((doc) => (
                        <Badge key={doc} variant="outline" className="text-xs">
                          {doc}
                        </Badge>
                      ))}
                      {template.typical_documents.length > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{template.typical_documents.length - 3} more
                        </Badge>
                      )}
                    </div>
                    
                    {/* Use Button */}
                    <Button
                      className="w-full mt-4 bg-slate-700 hover:bg-slate-600"
                      variant="secondary"
                    >
                      Use Template
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {filteredTemplates.length === 0 && (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No templates found</h3>
            <p className="text-slate-400 mb-4">Try adjusting your search or filter</p>
            <Button onClick={() => navigate("/lc-builder/dashboard/new")}>
              Start from Scratch
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

