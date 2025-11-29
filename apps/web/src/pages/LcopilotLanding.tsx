import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Shield, Zap, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";

const roles = [
  {
    id: "exporter",
    title: "I'm an Exporter",
    description: "Validate export LCs against UCP600/ISBP745, catch discrepancies before banks do, and ship with confidence.",
    to: "/lcopilot/exporter-dashboard",
    accent: "from-blue-500 to-blue-600",
    iconBg: "bg-blue-500/20",
  },
  {
    id: "importer",
    title: "I'm an Importer",
    description: "Screen supplier documents, manage LC applications, and reduce costly rejections before goods ship.",
    to: "/lcopilot/importer-dashboard",
    accent: "from-emerald-500 to-emerald-600",
    iconBg: "bg-emerald-500/20",
  },
  {
    id: "bank",
    title: "I'm a Bank",
    description: "Automate document examination, monitor compliance quality, and collaborate with clients in real time.",
    to: "/lcopilot/analytics/bank",
    accent: "from-purple-500 to-purple-600",
    iconBg: "bg-purple-500/20",
  },
];

const highlights = [
  {
    icon: <Zap className="w-6 h-6 text-blue-400" />,
    label: "45-Second Validation",
    description: "Upload your documents, get a full compliance report with actionable fixes in under a minute.",
  },
  {
    icon: <Shield className="w-6 h-6 text-emerald-400" />,
    label: "99% Accuracy",
    description: "AI-powered engine validates against 3,500+ rules from UCP600, ISBP745, and 60+ country regulations.",
  },
  {
    icon: <Globe className="w-6 h-6 text-purple-400" />,
    label: "Global Coverage",
    description: "Pre-built rules for Singapore, UAE, Bangladesh, India, EU, US, and 54 more jurisdictions.",
  },
];

const stats = [
  { value: "3,500+", label: "Rules Checked" },
  { value: "45s", label: "Avg. Validation" },
  { value: "99%", label: "Accuracy Rate" },
  { value: "$0", label: "To Start" },
];

export default function LcopilotLanding() {
  return (
    <div className="min-h-screen bg-slate-950">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24 relative z-10">
          <div className="max-w-3xl mb-12">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 mb-6">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              <span className="text-blue-400 text-sm font-medium">AI-Powered LC Validation</span>
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-white mb-6 leading-tight">
              Validate LCs in 45 seconds.
              <br />
              <span className="text-slate-400">Not 4 hours.</span>
            </h1>
            <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl">
              LCopilot checks your documents against UCP600, ISBP745, and 3,500+ validation rules. 
              Catch discrepancies before banks do. Stop paying $75 rejection fees.
            </p>
          </div>

          {/* Role Cards */}
          <div className="grid gap-6 lg:grid-cols-3">
            {roles.map((role) => (
              <div 
                key={role.id} 
                className="group relative bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-2xl p-8 hover:border-slate-700 transition-all duration-300"
              >
                {/* Gradient top bar */}
                <div className={`absolute inset-x-0 top-0 h-1 rounded-t-2xl bg-gradient-to-r ${role.accent}`} />
                
                <h2 className="text-2xl font-bold text-white mb-3">{role.title}</h2>
                <p className="text-slate-400 text-base leading-relaxed mb-6">
                  {role.description}
                </p>
                
                <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  <span>Role-specific dashboards • Tailored workflows</span>
                </div>
                
                <Button 
                  asChild 
                  size="lg" 
                  className={`w-full bg-gradient-to-r ${role.accent} hover:opacity-90 text-white font-semibold`}
                >
                  <Link to={role.to} className="flex items-center justify-center gap-2">
                    Get Started <ArrowRight className="w-4 h-4" />
                  </Link>
                </Button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Highlights Section */}
      <div className="border-t border-slate-800 bg-slate-900">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="grid gap-6 lg:grid-cols-3">
            {highlights.map((item, idx) => (
              <div 
                key={idx} 
                className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6"
              >
                <div className="flex items-center gap-4 mb-4">
                  <div className="bg-slate-700/50 p-3 rounded-lg">
                    {item.icon}
                  </div>
                  <h3 className="text-lg font-semibold text-white">{item.label}</h3>
                </div>
                <p className="text-slate-400 leading-relaxed">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="border-t border-slate-800 bg-slate-950">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="flex flex-col lg:flex-row items-center justify-between gap-10">
            <div className="lg:max-w-xl">
              <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
                Built for global trade.
                <br />
                <span className="text-slate-400">Works everywhere.</span>
              </h2>
              <p className="text-slate-400 leading-relaxed">
                Whether you process one LC a month or hundreds per day, LCopilot pairs AI validation 
                with human-ready workflows so your teams can ship documents without fear of rejection.
              </p>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {stats.map((stat) => (
                <div 
                  key={stat.label} 
                  className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center min-w-[120px]"
                >
                  <div className="text-3xl font-bold text-white mb-2">{stat.value}</div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="border-t border-slate-800 bg-slate-900/50">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
            <div>
              <p className="text-white font-semibold mb-1">Ready to validate your first LC?</p>
              <p className="text-slate-500 text-sm">Free to start. No credit card required.</p>
            </div>
            <div className="flex items-center gap-3">
              <Button 
                variant="outline" 
                className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
                asChild
              >
                <Link to="/">Learn More</Link>
              </Button>
              <Button 
                className="bg-white text-slate-900 hover:bg-slate-100 font-semibold"
                asChild
              >
                <Link to="/lcopilot/exporter-dashboard">
                  Start Free <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
