/**
 * Hub Billing - Subscription & Payment Management
 * 
 * Manage subscription plans, view usage, and handle billing.
 */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Check,
  CreditCard,
  Download,
  ExternalLink,
  Sparkles,
  TrendingUp,
  Zap,
  Clock,
  AlertCircle,
  Receipt,
  Calendar,
  DollarSign,
  Users,
  Shield,
  Infinity,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface Plan {
  slug: string;
  name: string;
  description?: string;
  price_monthly: number;
  price_yearly?: number;
  limits: Record<string, number>;
  overage_rates: Record<string, number>;
  features?: string[];
  max_users: number;
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
  cancel_at_period_end?: boolean;
}

interface UsageData {
  plan: string;
  plan_name: string;
  period_start?: string;
  period_end?: string;
  limits: Record<string, { limit: number | string; used: number; remaining: number | string }>;
}

interface CurrentUsage {
  period: { start: string; end: string };
  usage: Record<string, number>;
  overage: {
    lc_validations: number;
    price_checks: number;
    hs_lookups: number;
    sanctions_screens: number;
    container_tracks: number;
    total_charges: number;
  };
}

const PLAN_FEATURES: Record<string, string[]> = {
  payg: [
    "Pay only for what you use",
    "No monthly commitment",
    "All tools accessible",
    "Email support",
    "1 user",
  ],
  starter: [
    "5 LC validations/month",
    "25 price checks/month",
    "50 HS lookups/month",
    "Email support",
    "1 user",
    "Export reports",
  ],
  growth: [
    "15 LC validations/month",
    "75 price checks/month",
    "200 HS lookups/month",
    "Priority email support",
    "3 users",
    "API access",
    "Custom reports",
  ],
  pro: [
    "40 LC validations/month",
    "200 price checks/month",
    "500 HS lookups/month",
    "Priority support + chat",
    "10 users",
    "Full API access",
    "White-label reports",
    "SLA guarantee",
  ],
  enterprise: [
    "Unlimited validations",
    "Unlimited price checks",
    "Unlimited HS lookups",
    "Dedicated support",
    "Unlimited users",
    "Full API + webhooks",
    "White-label platform",
    "Custom integrations",
    "99.9% SLA",
  ],
};

export default function HubBilling() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [usage, setUsage] = useState<CurrentUsage | null>(null);
  const [limits, setLimits] = useState<UsageData | null>(null);
  const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">("monthly");

  useEffect(() => {
    fetchBillingData();
  }, []);

  const fetchBillingData = async () => {
    setLoading(true);
    try {
      // Fetch available plans
      const plansRes = await fetch(`${API_BASE}/usage/plans`);
      if (plansRes.ok) {
        const plansData = await plansRes.json();
        setPlans(plansData.plans || []);
      }

      // Fetch subscription info
      const subRes = await fetch(`${API_BASE}/usage/subscription`, {
        credentials: "include",
      });
      if (subRes.ok) {
        const subData = await subRes.json();
        setSubscription(subData);
      }

      // Fetch current usage
      const usageRes = await fetch(`${API_BASE}/usage/current`, {
        credentials: "include",
      });
      if (usageRes.ok) {
        const usageData = await usageRes.json();
        setUsage(usageData);
      }

      // Fetch limits
      const limitsRes = await fetch(`${API_BASE}/usage/limits`, {
        credentials: "include",
      });
      if (limitsRes.ok) {
        const limitsData = await limitsRes.json();
        setLimits(limitsData);
      }
    } catch (error) {
      console.error("Failed to fetch billing data:", error);
      toast({
        title: "Error",
        description: "Failed to load billing information",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = (plan: Plan) => {
    setSelectedPlan(plan);
    setUpgradeDialogOpen(true);
  };

  const confirmUpgrade = async () => {
    if (!selectedPlan) return;

    toast({
      title: "Upgrade Initiated",
      description: `Redirecting to checkout for ${selectedPlan.name} plan...`,
    });

    // In production, this would redirect to Stripe checkout
    // For now, just show a message
    setUpgradeDialogOpen(false);

    // Simulated checkout URL
    // window.location.href = `${API_BASE}/billing/checkout?plan=${selectedPlan.slug}&period=${billingPeriod}`;
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount);
  };

  const currentPlanSlug = subscription?.plan?.slug || "payg";

  const getUsagePercent = (operation: string) => {
    if (!limits?.limits) return 0;
    const data = limits.limits[operation];
    if (!data || typeof data.limit !== "number" || data.limit === 0) return 0;
    return Math.min((data.used / data.limit) * 100, 100);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-white/5 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate("/hub")}>
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Button>
            <div>
              <h1 className="text-xl font-semibold text-white">Billing & Plans</h1>
              <p className="text-sm text-slate-400">Manage your subscription and usage</p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Current Plan Overview */}
        <Card className="mb-8 bg-slate-900/50 border-white/5 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-emerald-500/5" />
          <CardHeader className="relative">
            <div className="flex items-center justify-between">
              <div>
                <CardDescription className="text-slate-400">Current Plan</CardDescription>
                <CardTitle className="text-2xl text-white flex items-center gap-3">
                  {subscription?.plan?.name || "Pay-as-you-go"}
                  <Badge
                    variant="outline"
                    className={`${
                      subscription?.status === "active"
                        ? "border-emerald-500/30 text-emerald-400"
                        : "border-amber-500/30 text-amber-400"
                    }`}
                  >
                    {subscription?.status || "Active"}
                  </Badge>
                </CardTitle>
              </div>
              {subscription?.has_subscription && subscription?.plan?.price_monthly && (
                <div className="text-right">
                  <p className="text-3xl font-bold text-white">
                    {formatCurrency(subscription.plan.price_monthly)}
                    <span className="text-sm text-slate-400 font-normal">/mo</span>
                  </p>
                  {subscription.current_period_end && (
                    <p className="text-sm text-slate-400">
                      Renews {formatDate(subscription.current_period_end)}
                    </p>
                  )}
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="relative">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Billing Period */}
              <div className="p-4 rounded-lg bg-slate-800/50 border border-white/5">
                <div className="flex items-center gap-2 text-slate-400 mb-2">
                  <Calendar className="w-4 h-4" />
                  <span className="text-sm">Billing Period</span>
                </div>
                <p className="text-white font-medium">
                  {usage?.period?.start && usage?.period?.end
                    ? `${formatDate(usage.period.start)} - ${formatDate(usage.period.end)}`
                    : "Monthly"}
                </p>
              </div>

              {/* Overage Charges */}
              <div className="p-4 rounded-lg bg-slate-800/50 border border-white/5">
                <div className="flex items-center gap-2 text-slate-400 mb-2">
                  <DollarSign className="w-4 h-4" />
                  <span className="text-sm">Overage This Month</span>
                </div>
                <p className="text-white font-medium">
                  {formatCurrency(usage?.overage?.total_charges || 0)}
                </p>
              </div>

              {/* Users */}
              <div className="p-4 rounded-lg bg-slate-800/50 border border-white/5">
                <div className="flex items-center gap-2 text-slate-400 mb-2">
                  <Users className="w-4 h-4" />
                  <span className="text-sm">Team Members</span>
                </div>
                <p className="text-white font-medium">
                  1 / {plans.find((p) => p.slug === currentPlanSlug)?.max_users || 1}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tabs: Usage / Plans / Invoices */}
        <Tabs defaultValue="usage" className="space-y-6">
          <TabsList className="bg-slate-800/50 border border-white/5">
            <TabsTrigger value="usage" className="data-[state=active]:bg-slate-700">
              Usage
            </TabsTrigger>
            <TabsTrigger value="plans" className="data-[state=active]:bg-slate-700">
              Plans
            </TabsTrigger>
            <TabsTrigger value="invoices" className="data-[state=active]:bg-slate-700">
              Invoices
            </TabsTrigger>
          </TabsList>

          {/* Usage Tab */}
          <TabsContent value="usage">
            <Card className="bg-slate-900/50 border-white/5">
              <CardHeader>
                <CardTitle className="text-white">Usage This Month</CardTitle>
                <CardDescription className="text-slate-400">
                  Track your usage across all tools
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* LC Validations */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white">LC Validations</span>
                    <span className="text-sm text-slate-400">
                      {usage?.usage?.lc_validations || 0} /{" "}
                      {limits?.limits?.lc_validations?.limit === "unlimited"
                        ? "∞"
                        : limits?.limits?.lc_validations?.limit || "∞"}
                    </span>
                  </div>
                  <Progress
                    value={getUsagePercent("lc_validations")}
                    className="h-2 bg-slate-800"
                  />
                  {usage?.overage?.lc_validations > 0 && (
                    <p className="text-xs text-amber-400 mt-1">
                      +{usage.overage.lc_validations} overage @ $5.00 each
                    </p>
                  )}
                </div>

                {/* Price Checks */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white">Price Checks</span>
                    <span className="text-sm text-slate-400">
                      {usage?.usage?.price_checks || 0} /{" "}
                      {limits?.limits?.price_checks?.limit === "unlimited"
                        ? "∞"
                        : limits?.limits?.price_checks?.limit || "∞"}
                    </span>
                  </div>
                  <Progress
                    value={getUsagePercent("price_checks")}
                    className="h-2 bg-slate-800"
                  />
                  {usage?.overage?.price_checks > 0 && (
                    <p className="text-xs text-amber-400 mt-1">
                      +{usage.overage.price_checks} overage @ $0.50 each
                    </p>
                  )}
                </div>

                {/* HS Lookups */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white">HS Code Lookups</span>
                    <span className="text-sm text-slate-400">
                      {usage?.usage?.hs_lookups || 0} /{" "}
                      {limits?.limits?.hs_lookups?.limit === "unlimited"
                        ? "∞"
                        : limits?.limits?.hs_lookups?.limit || "∞"}
                    </span>
                  </div>
                  <Progress
                    value={getUsagePercent("hs_lookups")}
                    className="h-2 bg-slate-800"
                  />
                </div>

                {/* Sanctions Screens */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white">Sanctions Screens</span>
                    <span className="text-sm text-slate-400">
                      {usage?.usage?.sanctions_screens || 0} /{" "}
                      {limits?.limits?.sanctions_screens?.limit === "unlimited"
                        ? "∞"
                        : limits?.limits?.sanctions_screens?.limit || "∞"}
                    </span>
                  </div>
                  <Progress
                    value={getUsagePercent("sanctions_screens")}
                    className="h-2 bg-slate-800"
                  />
                </div>

                {/* Container Tracks */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white">Container Tracks</span>
                    <span className="text-sm text-slate-400">
                      {usage?.usage?.container_tracks || 0} /{" "}
                      {limits?.limits?.container_tracks?.limit === "unlimited"
                        ? "∞"
                        : limits?.limits?.container_tracks?.limit || "∞"}
                    </span>
                  </div>
                  <Progress
                    value={getUsagePercent("container_tracks")}
                    className="h-2 bg-slate-800"
                  />
                </div>

                <Separator className="bg-white/5" />

                {/* Overage Summary */}
                {usage?.overage?.total_charges > 0 && (
                  <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 text-amber-400" />
                        <span className="text-amber-400 font-medium">Overage Charges</span>
                      </div>
                      <span className="text-xl font-bold text-white">
                        {formatCurrency(usage.overage.total_charges)}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400 mt-2">
                      Charges will be added to your next invoice. Consider upgrading to a higher
                      plan to avoid overage fees.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Plans Tab */}
          <TabsContent value="plans">
            {/* Billing Period Toggle */}
            <div className="flex items-center justify-center gap-4 mb-8">
              <span
                className={`text-sm ${billingPeriod === "monthly" ? "text-white" : "text-slate-500"}`}
              >
                Monthly
              </span>
              <button
                onClick={() =>
                  setBillingPeriod((p) => (p === "monthly" ? "yearly" : "monthly"))
                }
                className={`w-14 h-7 rounded-full p-1 transition-colors ${
                  billingPeriod === "yearly" ? "bg-emerald-500" : "bg-slate-700"
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-full bg-white transition-transform ${
                    billingPeriod === "yearly" ? "translate-x-7" : ""
                  }`}
                />
              </button>
              <span
                className={`text-sm flex items-center gap-1 ${
                  billingPeriod === "yearly" ? "text-white" : "text-slate-500"
                }`}
              >
                Yearly
                <Badge className="bg-emerald-500/20 text-emerald-400 text-xs">Save 20%</Badge>
              </span>
            </div>

            {/* Plans Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {plans.map((plan) => {
                const isCurrentPlan = plan.slug === currentPlanSlug;
                const features = PLAN_FEATURES[plan.slug] || [];
                const price =
                  billingPeriod === "yearly" && plan.price_yearly
                    ? plan.price_yearly / 12
                    : plan.price_monthly;

                return (
                  <Card
                    key={plan.slug}
                    className={`relative overflow-hidden transition-all ${
                      isCurrentPlan
                        ? "bg-gradient-to-br from-blue-500/10 to-emerald-500/10 border-emerald-500/30"
                        : "bg-slate-900/50 border-white/5 hover:border-white/20"
                    }`}
                  >
                    {isCurrentPlan && (
                      <div className="absolute top-0 right-0">
                        <Badge className="rounded-none rounded-bl-lg bg-emerald-500 text-white">
                          Current
                        </Badge>
                      </div>
                    )}
                    {plan.slug === "pro" && !isCurrentPlan && (
                      <div className="absolute top-0 right-0">
                        <Badge className="rounded-none rounded-bl-lg bg-gradient-to-r from-blue-500 to-emerald-500 text-white">
                          Popular
                        </Badge>
                      </div>
                    )}

                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg text-white">{plan.name}</CardTitle>
                      <div className="flex items-baseline gap-1">
                        <span className="text-3xl font-bold text-white">
                          {plan.price_monthly === 0 ? "Free" : formatCurrency(price)}
                        </span>
                        {plan.price_monthly > 0 && (
                          <span className="text-slate-400 text-sm">/mo</span>
                        )}
                      </div>
                      {billingPeriod === "yearly" && plan.price_yearly && (
                        <p className="text-xs text-emerald-400">
                          {formatCurrency(plan.price_yearly)} billed yearly
                        </p>
                      )}
                    </CardHeader>

                    <CardContent className="pt-0">
                      <ul className="space-y-2">
                        {features.slice(0, 6).map((feature, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm">
                            <Check className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                            <span className="text-slate-300">{feature}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>

                    <CardFooter>
                      {isCurrentPlan ? (
                        <Button disabled className="w-full bg-slate-800 text-slate-400">
                          Current Plan
                        </Button>
                      ) : plan.slug === "enterprise" ? (
                        <Button
                          variant="outline"
                          className="w-full border-white/10 text-white hover:bg-white/5"
                          onClick={() =>
                            (window.location.href = "mailto:sales@trdrhub.com?subject=Enterprise Plan Inquiry")
                          }
                        >
                          Contact Sales
                        </Button>
                      ) : (
                        <Button
                          className={`w-full ${
                            plan.slug === "pro"
                              ? "bg-gradient-to-r from-blue-500 to-emerald-500 hover:from-blue-600 hover:to-emerald-600"
                              : "bg-slate-800 hover:bg-slate-700"
                          } text-white`}
                          onClick={() => handleUpgrade(plan)}
                        >
                          {plans.findIndex((p) => p.slug === plan.slug) >
                          plans.findIndex((p) => p.slug === currentPlanSlug)
                            ? "Upgrade"
                            : "Switch"}
                        </Button>
                      )}
                    </CardFooter>
                  </Card>
                );
              })}
            </div>

            {/* Enterprise CTA */}
            <Card className="mt-8 bg-gradient-to-r from-slate-900 to-slate-800 border-white/10">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-white mb-2">
                      Need a custom solution?
                    </h3>
                    <p className="text-slate-400">
                      Enterprise plans include custom limits, dedicated support, SLA, and
                      white-labeling options.
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    className="border-white/20 text-white hover:bg-white/10"
                    onClick={() =>
                      (window.location.href = "mailto:sales@trdrhub.com?subject=Enterprise Plan Inquiry")
                    }
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Talk to Sales
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Invoices Tab */}
          <TabsContent value="invoices">
            <Card className="bg-slate-900/50 border-white/5">
              <CardHeader>
                <CardTitle className="text-white">Billing History</CardTitle>
                <CardDescription className="text-slate-400">
                  Download past invoices and receipts
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <Receipt className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-white mb-2">No invoices yet</h3>
                  <p className="text-slate-400 text-sm">
                    Your billing history will appear here once you have transactions.
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Upgrade Confirmation Dialog */}
      <Dialog open={upgradeDialogOpen} onOpenChange={setUpgradeDialogOpen}>
        <DialogContent className="bg-slate-900 border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white">
              Upgrade to {selectedPlan?.name}
            </DialogTitle>
            <DialogDescription className="text-slate-400">
              {billingPeriod === "yearly"
                ? `You'll be charged ${formatCurrency(selectedPlan?.price_yearly || 0)} annually.`
                : `You'll be charged ${formatCurrency(selectedPlan?.price_monthly || 0)} per month.`}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-slate-800/50 border border-white/5">
              <h4 className="text-sm font-medium text-white mb-2">What you'll get:</h4>
              <ul className="space-y-1">
                {PLAN_FEATURES[selectedPlan?.slug || ""]?.slice(0, 4).map((feature, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
                    <Check className="w-4 h-4 text-emerald-400" />
                    {feature}
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex items-center gap-2 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <Shield className="w-5 h-5 text-blue-400" />
              <span className="text-sm text-blue-300">
                30-day money-back guarantee. Cancel anytime.
              </span>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setUpgradeDialogOpen(false)}
              className="border-white/10 text-slate-300"
            >
              Cancel
            </Button>
            <Button
              onClick={confirmUpgrade}
              className="bg-gradient-to-r from-blue-500 to-emerald-500 text-white"
            >
              <CreditCard className="w-4 h-4 mr-2" />
              Proceed to Checkout
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

