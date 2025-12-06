import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  History,
  Search,
  Users,
  Ship,
  Package,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Download,
  Eye,
  Calendar,
  Filter,
} from "lucide-react";

// Mock data for demonstration
const mockHistory = [
  {
    id: "1",
    query: "Acme Trading Co Ltd",
    type: "party",
    status: "clear",
    screened_at: "2025-12-06T18:45:32Z",
    lists_screened: ["OFAC_SDN", "EU_CONS", "UN_SC"],
    certificate_id: "TRDR-20251206-A1B2C3",
  },
  {
    id: "2",
    query: "M/V PACIFIC TRADER",
    type: "vessel",
    status: "potential_match",
    screened_at: "2025-12-06T17:30:15Z",
    lists_screened: ["OFAC_SDN", "EU_CONS"],
    certificate_id: "TRDR-20251206-D4E5F6",
    match_score: 78,
  },
  {
    id: "3",
    query: "Industrial centrifuge equipment",
    type: "goods",
    status: "potential_match",
    screened_at: "2025-12-06T16:20:00Z",
    lists_screened: ["DUAL_USE", "COUNTRY_SANCTIONS"],
    certificate_id: "TRDR-20251206-G7H8I9",
    flags: ["Keyword detected: Nuclear/dual-use equipment"],
  },
];

export default function SanctionsHistory() {
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "clear": return CheckCircle;
      case "potential_match": return AlertTriangle;
      case "match": return XCircle;
      default: return History;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "clear": return "emerald";
      case "potential_match": return "amber";
      case "match": return "red";
      default: return "slate";
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "party": return Users;
      case "vessel": return Ship;
      case "goods": return Package;
      default: return Search;
    }
  };

  const filteredHistory = mockHistory.filter((item) => {
    if (searchQuery && !item.query.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (typeFilter !== "all" && item.type !== typeFilter) {
      return false;
    }
    if (statusFilter !== "all" && item.status !== statusFilter) {
      return false;
    }
    return true;
  });

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <History className="w-6 h-6 text-red-400" />
            Screening History
          </h1>
          <p className="text-slate-400 mt-1">
            View and download your past screening results
          </p>
        </div>
        <Button variant="outline" className="border-slate-700 text-slate-400 hover:text-white">
          <Download className="w-4 h-4 mr-2" />
          Export All
        </Button>
      </div>

      {/* Filters */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="p-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-500" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by name or query..."
                  className="pl-10 bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
                />
              </div>
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all" className="text-white">All Types</SelectItem>
                <SelectItem value="party" className="text-white">Party</SelectItem>
                <SelectItem value="vessel" className="text-white">Vessel</SelectItem>
                <SelectItem value="goods" className="text-white">Goods</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all" className="text-white">All Status</SelectItem>
                <SelectItem value="clear" className="text-white">Clear</SelectItem>
                <SelectItem value="potential_match" className="text-white">Potential Match</SelectItem>
                <SelectItem value="match" className="text-white">Match</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* History List */}
      <div className="space-y-3">
        {filteredHistory.length === 0 ? (
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-12 text-center">
              <History className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No screening history</h3>
              <p className="text-slate-400">
                {searchQuery || typeFilter !== "all" || statusFilter !== "all"
                  ? "No results match your filters"
                  : "Your screening history will appear here"}
              </p>
            </CardContent>
          </Card>
        ) : (
          filteredHistory.map((item) => {
            const StatusIcon = getStatusIcon(item.status);
            const TypeIcon = getTypeIcon(item.type);
            const statusColor = getStatusColor(item.status);

            return (
              <Card key={item.id} className="bg-slate-900/50 border-slate-800 hover:border-slate-700 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 bg-${statusColor}-500/20 rounded-lg flex items-center justify-center`}>
                        <StatusIcon className={`w-5 h-5 text-${statusColor}-400`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <TypeIcon className="w-4 h-4 text-slate-500" />
                          <span className="font-medium text-white">{item.query}</span>
                          <Badge variant="outline" className="border-slate-700 text-slate-400 text-xs">
                            {item.type}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(item.screened_at).toLocaleString()}
                          </span>
                          <span>{item.lists_screened.length} lists</span>
                          <span className="text-slate-600">{item.certificate_id}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge className={`bg-${statusColor}-500/20 text-${statusColor}-400 border-${statusColor}-500/30`}>
                        {item.status === "clear" && "Clear"}
                        {item.status === "potential_match" && "Review"}
                        {item.status === "match" && "Match"}
                      </Badge>
                      <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white">
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </Button>
                      <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white">
                        <Download className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}

