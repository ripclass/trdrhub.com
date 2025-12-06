import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Users,
  Ship,
  Package,
  ArrowRight,
  Shield,
  CheckCircle,
  AlertTriangle,
  Clock,
  TrendingUp,
  Database,
  RefreshCw,
} from "lucide-react";

const screeningTypes = [
  {
    id: "party",
    title: "Screen a Party",
    description: "Check buyers, sellers, banks, and agents against sanctions lists",
    icon: Users,
    href: "/sanctions/dashboard/screen/party",
    color: "red",
  },
  {
    id: "vessel",
    title: "Screen a Vessel",
    description: "Verify vessels against sanctioned flags, owners, and dark activity",
    icon: Ship,
    href: "/sanctions/dashboard/screen/vessel",
    color: "orange",
  },
  {
    id: "goods",
    title: "Screen Goods",
    description: "Check goods against dual-use and export control lists",
    icon: Package,
    href: "/sanctions/dashboard/screen/goods",
    color: "yellow",
  },
];

const stats = [
  { label: "Screenings Today", value: "0", icon: Clock },
  { label: "Clear Results", value: "0", icon: CheckCircle, color: "text-emerald-400" },
  { label: "Potential Matches", value: "0", icon: AlertTriangle, color: "text-amber-400" },
  { label: "Watchlist Items", value: "0", icon: TrendingUp },
];

const lists = [
  { name: "OFAC SDN", jurisdiction: "US", entries: "12,500+", updated: "Today" },
  { name: "EU Consolidated", jurisdiction: "EU", entries: "8,200+", updated: "3 days ago" },
  { name: "UN Security Council", jurisdiction: "UN", entries: "2,100+", updated: "Weekly" },
  { name: "UK OFSI", jurisdiction: "UK", entries: "4,800+", updated: "2 days ago" },
  { name: "BIS Entity List", jurisdiction: "US", entries: "600+", updated: "Monthly" },
];

export default function SanctionsOverview() {
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Sanctions Screener</h1>
          <p className="text-slate-400 mt-1">
            Screen parties, vessels, and goods against 50+ global sanctions lists
          </p>
        </div>
        <Badge variant="outline" className="border-emerald-500/50 text-emerald-400">
          <RefreshCw className="w-3 h-3 mr-1" />
          Lists Updated Today
        </Badge>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.label} className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide">{stat.label}</p>
                  <p className={`text-2xl font-bold ${stat.color || "text-white"}`}>
                    {stat.value}
                  </p>
                </div>
                <stat.icon className={`w-8 h-8 ${stat.color || "text-slate-600"}`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Screening Type Cards */}
      <div className="grid md:grid-cols-3 gap-4">
        {screeningTypes.map((type) => (
          <Card
            key={type.id}
            className="bg-slate-900/50 border-slate-800 hover:border-red-500/30 transition-all group"
          >
            <CardHeader>
              <div className={`w-12 h-12 bg-${type.color}-500/20 rounded-lg flex items-center justify-center mb-2`}>
                <type.icon className={`w-6 h-6 text-${type.color}-400`} />
              </div>
              <CardTitle className="text-white">{type.title}</CardTitle>
              <CardDescription className="text-slate-400">{type.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                asChild
                className="w-full bg-slate-800 hover:bg-red-500/20 text-white group-hover:text-red-400 group-hover:border-red-500/30"
              >
                <Link to={type.href}>
                  Start Screening <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Sanctions Lists Coverage */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-white flex items-center gap-2">
                <Database className="w-5 h-5 text-red-400" />
                Sanctions Lists Coverage
              </CardTitle>
              <CardDescription className="text-slate-400">
                We screen against 50+ global sanctions lists
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" className="border-slate-700 text-slate-400 hover:text-white">
              View All Lists
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase">List</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase">Jurisdiction</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase">Entries</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase">Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {lists.map((list) => (
                  <tr key={list.name} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4 text-red-400" />
                        <span className="text-white font-medium">{list.name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant="outline" className="border-slate-700 text-slate-400">
                        {list.jurisdiction}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-slate-400">{list.entries}</td>
                    <td className="py-3 px-4">
                      <span className="text-emerald-400 text-sm">{list.updated}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Quick Tips */}
      <Card className="bg-gradient-to-r from-red-500/10 to-orange-500/10 border-red-500/20">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
              <Shield className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white mb-2">Compliance Best Practices</h3>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>• Screen all parties before initiating any transaction</li>
                <li>• Verify vessels against sanctioned flags and ownership chains</li>
                <li>• Check goods for dual-use classification before export</li>
                <li>• Keep screening certificates for compliance audit trail</li>
                <li>• Set up watchlist monitoring for ongoing counterparties</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

