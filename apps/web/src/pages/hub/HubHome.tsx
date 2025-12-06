/**
 * Hub Home - Unified Dashboard for TRDR Hub
 * 
 * The central dashboard showing all user's tools, usage stats, and quick actions.
 * Works inside HubLayout with sidebar.
 */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { 
  FileCheck, 
  FileText,
  DollarSign, 
  Package, 
  Shield, 
  Ship, 
  TrendingUp,
  ChevronRight,
  Zap,
  Lock,
  Clock,
  AlertCircle,
  ArrowUpRight,
  Activity,
  Receipt,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { useUserRole } from "@/hooks/use-user-role";

const API_BASE = import.meta.env.VITE_API_URL || "";

// Tool definitions - ALL LIVE TOOLS
const TOOLS = [
  {
    id: "lcopilot",
    name: "LCopilot",
    description: "AI-powered LC validation against UCP600/ISBP rules",
    icon: FileCheck,
    color: "from-blue-500 to-blue-600",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/20",
    href: "/lcopilot/dashboard",
    operation: "lc_validations",
    pricePerUnit: 5.00,
  },
  {
    id: "lc_builder",
    name: "LC Builder",
    description: "Guided LC application builder with clause library",
    icon: Receipt,
    color: "from-emerald-500 to-emerald-600",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/20",
    href: "/lc-builder/dashboard",
    operation: "lc_applications",
    pricePerUnit: 2.00,
  },
  {
    id: "doc-generator",
    name: "Doc Generator",
    description: "Generate LC-compliant shipping documents",
    icon: FileText,
    color: "from-indigo-500 to-indigo-600",
    bgColor: "bg-indigo-500/10",
    borderColor: "border-indigo-500/20",
    href: "/doc-generator/dashboard",
    operation: "doc_sets",
    pricePerUnit: 0.25,
  },
  {
    id: "sanctions",
    name: "Sanctions Screener",
    description: "Real-time screening against global sanctions lists",
    icon: Shield,
    color: "from-red-500 to-red-600",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/20",
    href: "/sanctions/dashboard",
    operation: "sanctions_screens",
    pricePerUnit: 0.50,
  },
  {
    id: "hs_code",
    name: "HS Code Finder",
    description: "AI classification for customs tariff codes",
    icon: Package,
    color: "from-purple-500 to-purple-600",
    bgColor: "bg-purple-500/10",
    borderColor: "border-purple-500/20",
    href: "/hs-code/dashboard",
    operation: "hs_lookups",
    pricePerUnit: 0.25,
  },
  {
    id: "container",
    name: "Container Tracker",
    description: "Real-time shipment tracking across carriers",
    icon: Ship,
    color: "from-cyan-500 to-cyan-600",
    bgColor: "bg-cyan-500/10",
    borderColor: "border-cyan-500/20",
    href: "/tracking/dashboard",
    operation: "container_tracks",
    pricePerUnit: 1.00,
  },
  {
    id: "price_verify",
    name: "Price Verify",
    description: "TBML compliance - verify prices against market data",
    icon: DollarSign,
    color: "from-green-500 to-green-600",
    bgColor: "bg-green-500/10",
    borderColor: "border-green-500/20",
    href: "/price-verify/dashboard",
    operation: "price_checks",
    pricePerUnit: 0.50,
  },
];

interface UsageData {
  plan: string;
  plan_name: string;
  period_start?: string;
  period_end?: string;
  limits: Record<string, { limit: number | string; used: number; remaining: number | string }>;
}

interface SubscriptionData {
  has_subscription: boolean;
  plan: {
    slug: string;
    name: string;
    description?: string;
    price_monthly?: number;
    limits?: Record<string, number>;
    features?: string[];
  };
  status?: string;
  current_period_start?: string;
  current_period_end?: string;
}

interface RecentActivity {
  id: string;
  operation: string;
  tool: string;
  description?: string;
  created_at: string;
  is_overage: boolean;
}

export default function HubHome() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { role, isOwner, isAdmin, canAccessTool, canViewBilling, isLoading: roleLoading } = useUserRole();
  
  const [loading, setLoading] = useState(true);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [userName, setUserName] = useState("User");

  // Filter tools based on user's access
  const accessibleTools = TOOLS.filter(tool => {
    if (isOwner || isAdmin) return true; // Owner/Admin can see all
    return canAccessTool(tool.id);
  });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Fetch usage limits
      const limitsRes = await fetch(`${API_BASE}/usage/limits`, {
        credentials: "include",
      });
      if (limitsRes.ok) {
        const limitsData = await limitsRes.json();
        setUsage(limitsData);
      }

      // Fetch subscription info
      const subRes = await fetch(`${API_BASE}/usage/subscription`, {
        credentials: "include",
      });
      if (subRes.ok) {
        const subData = await subRes.json();
        setSubscription(subData);
      }

      // Fetch recent activity
      const logsRes = await fetch(`${API_BASE}/usage/logs?limit=5`, {
        credentials: "include",
      });
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setRecentActivity(logsData.logs || []);
      }

    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  const getToolUsage = (operation: string) => {
    if (!usage?.limits) return { used: 0, limit: "—", remaining: "—", percent: 0 };
    const data = usage.limits[operation];
    if (!data) return { used: 0, limit: "—", remaining: "—", percent: 0 };
    
    const limit = typeof data.limit === "number" ? data.limit : 0;
    const used = data.used || 0;
    const percent = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
    
    return {
      used,
      limit: data.limit === "unlimited" ? "∞" : data.limit,
      remaining: data.remaining === "unlimited" ? "∞" : data.remaining,
      percent,
    };
  };

  const getTotalUsagePercent = () => {
    if (!usage?.limits) return 0;
    let totalUsed = 0;
    let totalLimit = 0;
    
    Object.values(usage.limits).forEach((data) => {
      if (typeof data.limit === "number" && data.limit > 0) {
        totalUsed += data.used || 0;
        totalLimit += data.limit;
      }
    });
    
    return totalLimit > 0 ? Math.min((totalUsed / totalLimit) * 100, 100) : 0;
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const getOperationLabel = (operation: string) => {
    const labels: Record<string, string> = {
      lc_validation: "LC Validation",
      price_check: "Price Check",
      hs_lookup: "HS Code Lookup",
      sanctions_screen: "Sanctions Screen",
      container_track: "Container Track",
    };
    return labels[operation] || operation;
  };

  return (
    <div className="p-6 lg:p-8">
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">
          Welcome back{userName !== "User" ? `, ${userName}` : ""}! 👋
        </h1>
        <p className="text-slate-400">
          Your trade compliance toolkit • {subscription?.plan?.name || "Pay-as-you-go"} Plan
        </p>
      </div>

      {/* Usage Overview Card */}
      <Card className="mb-8 bg-slate-900/50 border-white/5 overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-emerald-400" />
                Usage This Month
              </CardTitle>
              <CardDescription className="text-slate-400">
                {usage?.period_start && usage?.period_end 
                  ? `${formatDate(usage.period_start)} - ${formatDate(usage.period_end)}`
                  : "Current billing period"
                }
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" className="border-white/10 text-slate-300" asChild>
              <Link to="/hub/usage">
                View Details
                <ChevronRight className="w-4 h-4 ml-1" />
              </Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-400">Overall Usage</span>
                <span className="text-sm font-medium text-white">{Math.round(getTotalUsagePercent())}%</span>
              </div>
              <Progress value={getTotalUsagePercent()} className="h-2 bg-slate-800" />
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 pt-2">
              {accessibleTools.filter(t => !t.comingSoon).map((tool) => {
                const toolUsage = getToolUsage(tool.operation);
                return (
                  <div key={tool.id} className="text-center">
                    <div className="text-2xl font-bold text-white">{toolUsage.used}</div>
                    <div className="text-xs text-slate-400">
                      / {toolUsage.limit} {tool.name.split(" ")[0]}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tools Grid */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">Your Tools</h2>
          <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white" asChild>
            <Link to="/tools">
              Browse All Tools
              <ArrowUpRight className="w-4 h-4 ml-1" />
            </Link>
          </Button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {accessibleTools.map((tool) => {
            const toolUsage = getToolUsage(tool.operation);
            const Icon = tool.icon;
            const isLocked = tool.comingSoon;
            
            return (
              <Card 
                key={tool.id}
                className={`group relative overflow-hidden transition-all duration-300 ${
                  isLocked 
                    ? "bg-slate-900/30 border-white/5 opacity-60" 
                    : `bg-slate-900/50 border-white/5 hover:border-white/20 hover:shadow-lg cursor-pointer`
                }`}
                onClick={() => !isLocked && navigate(tool.href)}
              >
                {/* Gradient overlay on hover */}
                {!isLocked && (
                  <div className={`absolute inset-0 bg-gradient-to-br ${tool.color} opacity-0 group-hover:opacity-5 transition-opacity`} />
                )}
                
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className={`p-3 rounded-xl ${tool.bgColor} ${tool.borderColor} border`}>
                      <Icon className="w-6 h-6" style={{ color: tool.color.includes('blue') ? '#3b82f6' : tool.color.includes('emerald') ? '#10b981' : tool.color.includes('purple') ? '#a855f7' : tool.color.includes('red') ? '#ef4444' : '#06b6d4' }} />
                    </div>
                    {isLocked ? (
                      <Badge variant="outline" className="border-slate-700 text-slate-500 text-xs">
                        <Lock className="w-3 h-3 mr-1" />
                        Coming Soon
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 text-xs">
                        <Zap className="w-3 h-3 mr-1" />
                        Active
                      </Badge>
                    )}
                  </div>
                  
                  <h3 className="text-lg font-semibold text-white mb-1">{tool.name}</h3>
                  <p className="text-sm text-slate-400 mb-4">{tool.description}</p>
                  
                  {!isLocked && (
                    <div className="flex items-center justify-between pt-3 border-t border-white/5">
                      <div className="text-sm">
                        <span className="text-white font-medium">{toolUsage.used}</span>
                        <span className="text-slate-500"> / {toolUsage.limit} used</span>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-white transition-colors" />
                    </div>
                  )}
                  
                  {isLocked && (
                    <div className="flex items-center justify-between pt-3 border-t border-white/5">
                      <div className="text-sm text-slate-500">
                        ${tool.pricePerUnit.toFixed(2)} per use
                      </div>
                      <Button size="sm" variant="ghost" className="text-slate-400 h-7 px-2">
                        Notify Me
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Bottom Section: Recent Activity + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <Card className="lg:col-span-2 bg-slate-900/50 border-white/5">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue-400" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recentActivity.length > 0 ? (
              <div className="space-y-3">
                {recentActivity.map((activity) => (
                  <div 
                    key={activity.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-white/5"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        activity.operation === "lc_validation" ? "bg-blue-500/10" :
                        activity.operation === "price_check" ? "bg-emerald-500/10" :
                        "bg-purple-500/10"
                      }`}>
                        {activity.operation === "lc_validation" ? (
                          <FileCheck className="w-4 h-4 text-blue-400" />
                        ) : activity.operation === "price_check" ? (
                          <DollarSign className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <Package className="w-4 h-4 text-purple-400" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">
                          {getOperationLabel(activity.operation)}
                        </p>
                        <p className="text-xs text-slate-400">
                          {activity.description || `via ${activity.tool}`}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-slate-400">{formatTimeAgo(activity.created_at)}</p>
                      {activity.is_overage && (
                        <Badge variant="outline" className="border-amber-500/30 text-amber-400 text-xs mt-1">
                          Overage
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Activity className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400">No recent activity</p>
                <p className="text-sm text-slate-500 mt-1">Start using tools to see activity here</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="bg-slate-900/50 border-white/5">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-400" />
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button 
              className="w-full justify-start bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20"
              variant="outline"
              onClick={() => navigate("/lcopilot/dashboard")}
            >
              <FileCheck className="w-4 h-4 mr-2" />
              Validate New LC
            </Button>
            
            <Button 
              className="w-full justify-start bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20"
              variant="outline"
              onClick={() => navigate("/price-verify/dashboard/verify")}
            >
              <DollarSign className="w-4 h-4 mr-2" />
              Verify Price
            </Button>
            
            <Separator className="bg-white/5" />
            
            <Button 
              className="w-full justify-start text-slate-400 hover:text-white"
              variant="ghost"
              onClick={() => navigate("/hub/billing")}
            >
              <TrendingUp className="w-4 h-4 mr-2" />
              Upgrade Plan
            </Button>
            
            <Button 
              className="w-full justify-start text-slate-400 hover:text-white"
              variant="ghost"
              onClick={() => navigate("/support")}
            >
              <AlertCircle className="w-4 h-4 mr-2" />
              Get Support
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Upgrade CTA (for non-enterprise users) */}
      {subscription?.plan?.slug !== "enterprise" && subscription?.plan?.slug !== "pro" && (
        <Card className="mt-8 bg-gradient-to-r from-blue-500/10 to-emerald-500/10 border-white/10 overflow-hidden">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white mb-1">
                  Upgrade to {subscription?.plan?.slug === "starter" ? "Growth" : "Starter"} Plan
                </h3>
                <p className="text-slate-400 text-sm">
                  Get more validations, priority support, and API access
                </p>
              </div>
              <Button 
                className="bg-gradient-to-r from-blue-500 to-emerald-500 hover:from-blue-600 hover:to-emerald-600 text-white"
                onClick={() => navigate("/hub/billing")}
              >
                <TrendingUp className="w-4 h-4 mr-2" />
                Upgrade Now
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
