/**
 * Clause Library Page
 * 
 * Browse and search 428+ pre-approved LC clauses organized by category.
 */

import { useState, useEffect } from "react";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Search,
  Copy,
  BookOpen,
  Ship,
  FileText,
  CreditCard,
  Sparkles,
  FileEdit,
  Coins,
  AlertTriangle,
  Shield,
  CheckCircle,
  Info,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface Clause {
  code: string;
  category: string;
  subcategory: string;
  title: string;
  clause_text: string;
  plain_english: string;
  risk_level: string;
  bias: string;
  risk_notes: string;
  bank_acceptance: number;
  tags: string[];
}

interface ClauseStats {
  total_clauses: number;
  categories: Record<string, number>;
  by_risk_level: Record<string, number>;
  by_bias: Record<string, number>;
}

const categoryIcons: Record<string, React.ElementType> = {
  shipment: Ship,
  documents: FileText,
  payment: CreditCard,
  special: Sparkles,
  amendments: FileEdit,
  red_green: Coins,
};

const categoryColors: Record<string, string> = {
  shipment: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  documents: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  payment: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  special: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  amendments: "bg-pink-500/10 text-pink-400 border-pink-500/20",
  red_green: "bg-red-500/10 text-red-400 border-red-500/20",
};

const riskColors: Record<string, string> = {
  low: "bg-green-500/10 text-green-400",
  medium: "bg-yellow-500/10 text-yellow-400",
  high: "bg-red-500/10 text-red-400",
};

const biasColors: Record<string, string> = {
  beneficiary: "bg-blue-500/10 text-blue-400",
  applicant: "bg-purple-500/10 text-purple-400",
  neutral: "bg-slate-500/10 text-slate-400",
};

export default function ClauseLibraryPage() {
  const { session } = useAuth();
  const { toast } = useToast();
  
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [filteredClauses, setFilteredClauses] = useState<Clause[]>([]);
  const [stats, setStats] = useState<ClauseStats | null>(null);
  const [loading, setLoading] = useState(true);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [biasFilter, setBiasFilter] = useState("all");
  
  const [selectedClause, setSelectedClause] = useState<Clause | null>(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);

  useEffect(() => {
    fetchClauses();
  }, [session?.access_token]);

  useEffect(() => {
    filterClauses();
  }, [clauses, searchQuery, categoryFilter, riskFilter, biasFilter]);

  const fetchClauses = async () => {
    setLoading(true);
    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }

      // Fetch clauses
      const clausesRes = await fetch(`${API_BASE}/lc-builder/clauses`, { headers });
      if (clausesRes.ok) {
        const data = await clausesRes.json();
        setClauses(data.clauses || []);
        setStats(data.statistics || null);
      }
    } catch (error) {
      console.error("Error fetching clauses:", error);
      toast({
        title: "Error",
        description: "Failed to load clause library",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const filterClauses = () => {
    let filtered = [...clauses];
    
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.title.toLowerCase().includes(query) ||
          c.clause_text.toLowerCase().includes(query) ||
          c.plain_english.toLowerCase().includes(query) ||
          c.tags.some((t) => t.toLowerCase().includes(query))
      );
    }
    
    // Category filter
    if (categoryFilter !== "all") {
      filtered = filtered.filter((c) => c.category === categoryFilter);
    }
    
    // Risk filter
    if (riskFilter !== "all") {
      filtered = filtered.filter((c) => c.risk_level === riskFilter);
    }
    
    // Bias filter
    if (biasFilter !== "all") {
      filtered = filtered.filter((c) => c.bias === biasFilter);
    }
    
    setFilteredClauses(filtered);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied!",
      description: "Clause text copied to clipboard",
    });
  };

  const openClauseDetail = (clause: Clause) => {
    setSelectedClause(clause);
    setShowDetailDialog(true);
  };

  // Group clauses by subcategory for better organization
  const groupedClauses = filteredClauses.reduce((acc, clause) => {
    const key = `${clause.category}|${clause.subcategory}`;
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(clause);
    return acc;
  }, {} as Record<string, Clause[]>);

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-emerald-400" />
                Clause Library
              </h1>
              <p className="text-sm text-slate-400">
                {stats?.total_clauses || 0} pre-approved LC clauses across {Object.keys(stats?.categories || {}).length} categories
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="px-6 py-4 border-b border-slate-800">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            {Object.entries(stats.categories).map(([cat, count]) => {
              const Icon = categoryIcons[cat] || FileText;
              return (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat === categoryFilter ? "all" : cat)}
                  className={`p-3 rounded-lg border transition-all ${
                    categoryFilter === cat
                      ? "border-emerald-500 bg-emerald-500/10"
                      : "border-slate-700 bg-slate-800/50 hover:border-slate-600"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-slate-400" />
                    <span className="text-sm font-medium text-white capitalize">{cat}</span>
                  </div>
                  <p className="text-lg font-bold text-emerald-400 mt-1">{count}</p>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="px-6 py-4 border-b border-slate-800">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search clauses..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-slate-800 border-slate-700"
              />
            </div>
          </div>
          
          <Select value={riskFilter} onValueChange={setRiskFilter}>
            <SelectTrigger className="w-[150px] bg-slate-800 border-slate-700">
              <SelectValue placeholder="Risk Level" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Risk Levels</SelectItem>
              <SelectItem value="low">Low Risk</SelectItem>
              <SelectItem value="medium">Medium Risk</SelectItem>
              <SelectItem value="high">High Risk</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={biasFilter} onValueChange={setBiasFilter}>
            <SelectTrigger className="w-[150px] bg-slate-800 border-slate-700">
              <SelectValue placeholder="Bias" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Parties</SelectItem>
              <SelectItem value="beneficiary">Pro-Beneficiary</SelectItem>
              <SelectItem value="applicant">Pro-Applicant</SelectItem>
              <SelectItem value="neutral">Neutral</SelectItem>
            </SelectContent>
          </Select>
          
          {(categoryFilter !== "all" || riskFilter !== "all" || biasFilter !== "all" || searchQuery) && (
            <Button
              variant="ghost"
              onClick={() => {
                setCategoryFilter("all");
                setRiskFilter("all");
                setBiasFilter("all");
                setSearchQuery("");
              }}
              className="text-slate-400"
            >
              Clear Filters
            </Button>
          )}
        </div>
        
        <p className="text-sm text-slate-400 mt-2">
          Showing {filteredClauses.length} of {clauses.length} clauses
        </p>
      </div>

      {/* Clauses List */}
      <div className="px-6 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
          </div>
        ) : filteredClauses.length === 0 ? (
          <div className="text-center py-12">
            <BookOpen className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No clauses found</h3>
            <p className="text-slate-400">Try adjusting your search or filters</p>
          </div>
        ) : (
          <Accordion type="multiple" className="space-y-4">
            {Object.entries(groupedClauses).map(([key, groupClauses]) => {
              const [category, subcategory] = key.split("|");
              const Icon = categoryIcons[category] || FileText;
              
              return (
                <AccordionItem
                  key={key}
                  value={key}
                  className="border border-slate-700 rounded-lg bg-slate-800/30"
                >
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${categoryColors[category]?.split(" ")[0] || "bg-slate-700"}`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="text-left">
                        <p className="font-medium text-white">{subcategory}</p>
                        <p className="text-xs text-slate-400">{groupClauses.length} clauses</p>
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <div className="space-y-3">
                      {groupClauses.map((clause) => (
                        <Card
                          key={clause.code}
                          className="bg-slate-800/50 border-slate-700 hover:border-slate-600 cursor-pointer transition-all"
                          onClick={() => openClauseDetail(clause)}
                        >
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <Badge variant="outline" className="text-xs">
                                    {clause.code}
                                  </Badge>
                                  <Badge className={riskColors[clause.risk_level]}>
                                    {clause.risk_level}
                                  </Badge>
                                  <Badge className={biasColors[clause.bias]}>
                                    {clause.bias}
                                  </Badge>
                                </div>
                                <h4 className="font-medium text-white mb-1">
                                  {clause.title}
                                </h4>
                                <p className="text-sm text-slate-400 line-clamp-2">
                                  {clause.plain_english}
                                </p>
                              </div>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  copyToClipboard(clause.clause_text);
                                }}
                              >
                                <Copy className="h-4 w-4" />
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              );
            })}
          </Accordion>
        )}
      </div>

      {/* Clause Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedClause && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Badge variant="outline">{selectedClause.code}</Badge>
                  {selectedClause.title}
                </DialogTitle>
                <DialogDescription>
                  {selectedClause.subcategory}
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4 mt-4">
                {/* Badges */}
                <div className="flex flex-wrap gap-2">
                  <Badge className={categoryColors[selectedClause.category]}>
                    {selectedClause.category}
                  </Badge>
                  <Badge className={riskColors[selectedClause.risk_level]}>
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    {selectedClause.risk_level} risk
                  </Badge>
                  <Badge className={biasColors[selectedClause.bias]}>
                    <Shield className="h-3 w-3 mr-1" />
                    {selectedClause.bias}
                  </Badge>
                  {selectedClause.bank_acceptance > 0 && (
                    <Badge className="bg-green-500/10 text-green-400">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      {Math.round(selectedClause.bank_acceptance * 100)}% acceptance
                    </Badge>
                  )}
                </div>
                
                {/* Clause Text */}
                <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-xs text-slate-400 mb-2">CLAUSE TEXT</p>
                      <p className="text-white font-mono text-sm">
                        {selectedClause.clause_text}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => copyToClipboard(selectedClause.clause_text)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                
                {/* Plain English */}
                <div className="bg-emerald-500/5 rounded-lg p-4 border border-emerald-500/20">
                  <div className="flex items-start gap-2">
                    <Info className="h-5 w-5 text-emerald-400 mt-0.5" />
                    <div>
                      <p className="text-xs text-emerald-400 mb-1">PLAIN ENGLISH</p>
                      <p className="text-slate-300">{selectedClause.plain_english}</p>
                    </div>
                  </div>
                </div>
                
                {/* Risk Notes */}
                {selectedClause.risk_notes && (
                  <div className="bg-yellow-500/5 rounded-lg p-4 border border-yellow-500/20">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="h-5 w-5 text-yellow-400 mt-0.5" />
                      <div>
                        <p className="text-xs text-yellow-400 mb-1">RISK NOTES</p>
                        <p className="text-slate-300">{selectedClause.risk_notes}</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Tags */}
                {selectedClause.tags.length > 0 && (
                  <div>
                    <p className="text-xs text-slate-400 mb-2">TAGS</p>
                    <div className="flex flex-wrap gap-2">
                      {selectedClause.tags.map((tag) => (
                        <Badge
                          key={tag}
                          variant="outline"
                          className="text-xs cursor-pointer hover:bg-slate-700"
                          onClick={() => {
                            setSearchQuery(tag);
                            setShowDetailDialog(false);
                          }}
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Action Buttons */}
                <div className="flex gap-2 pt-4">
                  <Button
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                    onClick={() => copyToClipboard(selectedClause.clause_text)}
                  >
                    <Copy className="h-4 w-4 mr-2" />
                    Copy Clause
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

