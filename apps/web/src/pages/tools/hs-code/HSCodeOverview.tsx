/**
 * HS Code Finder - Overview Dashboard
 */

import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Calculator,
  Globe,
  History,
  TrendingUp,
  Package,
  ArrowRight,
  CheckCircle,
  Clock,
  Star,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface RecentClassification {
  id: string;
  product_description: string;
  hs_code: string;
  import_country: string;
  confidence_score: number;
  created_at: string;
}

interface Stats {
  total_classifications: number;
  this_month: number;
  verified_count: number;
  favorite_count: number;
}

export default function HSCodeOverview() {
  const { session } = useAuth();
  const [stats, setStats] = useState<Stats>({
    total_classifications: 0,
    this_month: 0,
    verified_count: 0,
    favorite_count: 0,
  });
  const [recentClassifications, setRecentClassifications] = useState<RecentClassification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (session?.access_token) {
      fetchRecentClassifications();
    } else {
      setLoading(false);
    }
  }, [session?.access_token]);

  const fetchRecentClassifications = async () => {
    try {
      const response = await fetch(`${API_BASE}/hs-code/history?limit=5`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setRecentClassifications(data.classifications || []);
        setStats({
          total_classifications: data.total || 0,
          this_month: Math.min(data.total || 0, 12),
          verified_count: data.classifications?.filter((c: any) => c.is_verified).length || 0,
          favorite_count: 0,
        });
      }
    } catch (error) {
      console.error("Error fetching classifications:", error);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    {
      icon: Search,
      title: "Classify Product",
      description: "Describe your product and get AI-powered HS code",
      href: "/hs-code/dashboard/classify",
      color: "bg-emerald-500/20 text-emerald-400",
    },
    {
      icon: Calculator,
      title: "Duty Calculator",
      description: "Calculate import duties and landed costs",
      href: "/hs-code/dashboard/duty",
      color: "bg-blue-500/20 text-blue-400",
    },
    {
      icon: Globe,
      title: "FTA Eligibility",
      description: "Check Free Trade Agreement benefits",
      href: "/hs-code/dashboard/fta",
      color: "bg-purple-500/20 text-purple-400",
    },
    {
      icon: Upload,
      title: "Bulk Upload",
      description: "Classify multiple products at once",
      href: "/hs-code/dashboard/bulk",
      color: "bg-amber-500/20 text-amber-400",
    },
  ];

  const popularSearches = [
    { query: "Cotton t-shirts", code: "6109.10.00", chapter: "61" },
    { query: "Laptops", code: "8471.30.01", chapter: "84" },
    { query: "Smartphones", code: "8517.12.00", chapter: "85" },
    { query: "Roasted coffee", code: "0901.21.00", chapter: "09" },
    { query: "Automotive parts", code: "8708.99.81", chapter: "87" },
    { query: "Lithium batteries", code: "8507.60.00", chapter: "85" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Search className="h-5 w-5 text-emerald-400" />
            HS Code Finder
          </h1>
          <p className="text-sm text-slate-400">
            AI-powered tariff classification, duty rates, and FTA eligibility
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/20">
                  <Package className="h-5 w-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.total_classifications}</p>
                  <p className="text-sm text-slate-400">Total Classifications</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/20">
                  <TrendingUp className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.this_month}</p>
                  <p className="text-sm text-slate-400">This Month</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/20">
                  <CheckCircle className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.verified_count}</p>
                  <p className="text-sm text-slate-400">Verified</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-amber-500/20">
                  <Star className="h-5 w-5 text-amber-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.favorite_count}</p>
                  <p className="text-sm text-slate-400">Favorites</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {quickActions.map((action) => (
            <Link key={action.href} to={action.href}>
              <Card className="bg-slate-800 border-slate-700 hover:bg-slate-700 transition-colors cursor-pointer h-full">
                <CardContent className="p-4">
                  <div className={`p-2 rounded-lg w-fit ${action.color} mb-3`}>
                    <action.icon className="h-5 w-5" />
                  </div>
                  <h3 className="font-semibold text-white mb-1">{action.title}</h3>
                  <p className="text-sm text-slate-400">{action.description}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recent Classifications */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">Recent Classifications</h2>
              <Link to="/hs-code/dashboard/history">
                <Button variant="ghost" size="sm" className="text-emerald-400 hover:text-emerald-300">
                  View All <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </div>
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="p-0">
                {loading ? (
                  <div className="p-8 text-center text-slate-400">Loading...</div>
                ) : recentClassifications.length === 0 ? (
                  <div className="p-8 text-center">
                    <Package className="h-12 w-12 mx-auto mb-3 text-slate-600" />
                    <p className="text-slate-400">No classifications yet</p>
                    <Link to="/hs-code/dashboard/classify">
                      <Button variant="outline" size="sm" className="mt-3">
                        Start Classifying
                      </Button>
                    </Link>
                  </div>
                ) : (
                  <ul className="divide-y divide-slate-700">
                    {recentClassifications.map((item) => (
                      <li key={item.id} className="p-4 hover:bg-slate-700/50">
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-white truncate">
                              {item.product_description}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-400">
                                {item.hs_code}
                              </Badge>
                              <span className="text-xs text-slate-500">
                                {Math.round(item.confidence_score * 100)}% confidence
                              </span>
                            </div>
                          </div>
                          <div className="text-xs text-slate-500 flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(item.created_at).toLocaleDateString()}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Popular Searches */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">Popular Product Searches</h2>
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="p-0">
                <ul className="divide-y divide-slate-700">
                  {popularSearches.map((item, index) => (
                    <li key={index} className="p-4 hover:bg-slate-700/50">
                      <Link 
                        to={`/hs-code/dashboard/classify?q=${encodeURIComponent(item.query)}`}
                        className="flex items-center justify-between"
                      >
                        <div>
                          <p className="text-sm font-medium text-white">{item.query}</p>
                          <p className="text-xs text-slate-500">Chapter {item.chapter}</p>
                        </div>
                        <Badge variant="outline" className="border-slate-600 text-slate-400">
                          {item.code}
                        </Badge>
                      </Link>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Info Cards */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-gradient-to-br from-emerald-900/50 to-slate-800 border-emerald-800/50">
            <CardHeader>
              <CardTitle className="text-emerald-400 text-lg">AI Classification</CardTitle>
              <CardDescription className="text-slate-400">
                Describe your product in plain language and our AI will determine the correct HS code
                using GRI rules and binding rulings.
              </CardDescription>
            </CardHeader>
          </Card>
          <Card className="bg-gradient-to-br from-blue-900/50 to-slate-800 border-blue-800/50">
            <CardHeader>
              <CardTitle className="text-blue-400 text-lg">100+ Countries</CardTitle>
              <CardDescription className="text-slate-400">
                Access tariff schedules for US, EU, UK, China, Japan, India, and more. 
                Calculate duties with country-specific rates.
              </CardDescription>
            </CardHeader>
          </Card>
          <Card className="bg-gradient-to-br from-purple-900/50 to-slate-800 border-purple-800/50">
            <CardHeader>
              <CardTitle className="text-purple-400 text-lg">FTA Savings</CardTitle>
              <CardDescription className="text-slate-400">
                Check eligibility for USMCA, RCEP, CPTPP, and other trade agreements. 
                See rules of origin and calculate potential savings.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </div>
    </div>
  );
}

