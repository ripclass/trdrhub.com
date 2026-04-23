import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { 
  Package, 
  PackageOpen, 
  RefreshCw, 
  Truck, 
  Building2,
  User, 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  Landmark, 
  ArrowRight,
  ArrowLeft,
  Check,
  Gift,
  Users,
  Building,
  Factory,
  FileCheck,
  DollarSign,
  Ship,
  Shield,
  Globe,
  ChevronDown,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import {
  completeOnboarding as completeOnboardingRequest,
  sortActivitiesByPriority,
  type BusinessActivity,
  type BusinessTier,
} from "@/api/onboarding";

// ─────────────────────────────────────────────────────────────
// Types & Constants — aligned with the post-auth OnboardingWizard
// (apps/web/src/components/onboarding/OnboardingWizard.tsx) and the
// backend Company.business_activities / Company.tier columns.
// See REGISTER_WIZARD_ALIGNMENT.md at repo root.
// ─────────────────────────────────────────────────────────────

interface CompanyTypeOption {
  value: BusinessActivity;
  label: string;
  description: string;
  icon: React.ElementType;
}

interface CompanySizeOption {
  value: BusinessTier;
  label: string;
  employees: string;
  icon: React.ElementType;
}

const COMPANY_TYPES: CompanyTypeOption[] = [
  {
    value: "exporter",
    label: "Exporter",
    description: "We export goods",
    icon: Package,
  },
  {
    value: "importer",
    label: "Importer",
    description: "We import goods",
    icon: PackageOpen,
  },
  {
    value: "agent",
    label: "Sourcing agent",
    description: "We manage LCs for buyers",
    icon: Users,
  },
  {
    value: "services",
    label: "Trade services",
    description: "Freight / broker / consultant",
    icon: Truck,
  },
];

const COMPANY_SIZES: CompanySizeOption[] = [
  {
    value: "solo",
    label: "Solo",
    employees: "1-3 people",
    icon: User,
  },
  {
    value: "sme",
    label: "SME",
    employees: "4-20 people",
    icon: Users,
  },
  {
    value: "enterprise",
    label: "Enterprise",
    employees: "21+, SSO + audit log",
    icon: Factory,
  },
];

const FEATURES = [
  { icon: FileCheck, label: "LC Validation", desc: "UCP600 compliance" },
  { icon: DollarSign, label: "Price Verify", desc: "Market benchmarks" },
  { icon: Ship, label: "Track Shipments", desc: "Real-time updates" },
  { icon: Shield, label: "Sanctions Check", desc: "OFAC, EU, UN" },
];

// Country options with payment gateway mapping
interface CountryOption {
  code: string;
  name: string;
  flag: string;
  currency: string;
  currencySymbol: string;
  paymentGateway: "stripe" | "sslcommerz" | "razorpay" | "local";
}

const COUNTRIES: CountryOption[] = [
  // South Asia (Local gateways)
  { code: "BD", name: "Bangladesh", flag: "🇧🇩", currency: "BDT", currencySymbol: "৳", paymentGateway: "sslcommerz" },
  { code: "IN", name: "India", flag: "🇮🇳", currency: "INR", currencySymbol: "₹", paymentGateway: "razorpay" },
  { code: "PK", name: "Pakistan", flag: "🇵🇰", currency: "PKR", currencySymbol: "Rs", paymentGateway: "local" },
  { code: "LK", name: "Sri Lanka", flag: "🇱🇰", currency: "LKR", currencySymbol: "Rs", paymentGateway: "local" },
  { code: "NP", name: "Nepal", flag: "🇳🇵", currency: "NPR", currencySymbol: "Rs", paymentGateway: "local" },
  // Middle East
  { code: "AE", name: "United Arab Emirates", flag: "🇦🇪", currency: "AED", currencySymbol: "د.إ", paymentGateway: "stripe" },
  { code: "SA", name: "Saudi Arabia", flag: "🇸🇦", currency: "SAR", currencySymbol: "﷼", paymentGateway: "stripe" },
  // Southeast Asia
  { code: "SG", name: "Singapore", flag: "🇸🇬", currency: "SGD", currencySymbol: "S$", paymentGateway: "stripe" },
  { code: "MY", name: "Malaysia", flag: "🇲🇾", currency: "MYR", currencySymbol: "RM", paymentGateway: "stripe" },
  { code: "ID", name: "Indonesia", flag: "🇮🇩", currency: "IDR", currencySymbol: "Rp", paymentGateway: "local" },
  { code: "TH", name: "Thailand", flag: "🇹🇭", currency: "THB", currencySymbol: "฿", paymentGateway: "stripe" },
  { code: "VN", name: "Vietnam", flag: "🇻🇳", currency: "VND", currencySymbol: "₫", paymentGateway: "local" },
  { code: "PH", name: "Philippines", flag: "🇵🇭", currency: "PHP", currencySymbol: "₱", paymentGateway: "stripe" },
  // East Asia
  { code: "CN", name: "China", flag: "🇨🇳", currency: "CNY", currencySymbol: "¥", paymentGateway: "local" },
  { code: "HK", name: "Hong Kong", flag: "🇭🇰", currency: "HKD", currencySymbol: "HK$", paymentGateway: "stripe" },
  { code: "JP", name: "Japan", flag: "🇯🇵", currency: "JPY", currencySymbol: "¥", paymentGateway: "stripe" },
  { code: "KR", name: "South Korea", flag: "🇰🇷", currency: "KRW", currencySymbol: "₩", paymentGateway: "stripe" },
  { code: "TW", name: "Taiwan", flag: "🇹🇼", currency: "TWD", currencySymbol: "NT$", paymentGateway: "stripe" },
  // Europe
  { code: "GB", name: "United Kingdom", flag: "🇬🇧", currency: "GBP", currencySymbol: "£", paymentGateway: "stripe" },
  { code: "DE", name: "Germany", flag: "🇩🇪", currency: "EUR", currencySymbol: "€", paymentGateway: "stripe" },
  { code: "FR", name: "France", flag: "🇫🇷", currency: "EUR", currencySymbol: "€", paymentGateway: "stripe" },
  { code: "NL", name: "Netherlands", flag: "🇳🇱", currency: "EUR", currencySymbol: "€", paymentGateway: "stripe" },
  { code: "IT", name: "Italy", flag: "🇮🇹", currency: "EUR", currencySymbol: "€", paymentGateway: "stripe" },
  { code: "ES", name: "Spain", flag: "🇪🇸", currency: "EUR", currencySymbol: "€", paymentGateway: "stripe" },
  { code: "TR", name: "Turkey", flag: "🇹🇷", currency: "TRY", currencySymbol: "₺", paymentGateway: "stripe" },
  // Americas
  { code: "US", name: "United States", flag: "🇺🇸", currency: "USD", currencySymbol: "$", paymentGateway: "stripe" },
  { code: "CA", name: "Canada", flag: "🇨🇦", currency: "CAD", currencySymbol: "C$", paymentGateway: "stripe" },
  { code: "MX", name: "Mexico", flag: "🇲🇽", currency: "MXN", currencySymbol: "$", paymentGateway: "stripe" },
  { code: "BR", name: "Brazil", flag: "🇧🇷", currency: "BRL", currencySymbol: "R$", paymentGateway: "stripe" },
  // Africa
  { code: "NG", name: "Nigeria", flag: "🇳🇬", currency: "NGN", currencySymbol: "₦", paymentGateway: "local" },
  { code: "KE", name: "Kenya", flag: "🇰🇪", currency: "KES", currencySymbol: "KSh", paymentGateway: "local" },
  { code: "ZA", name: "South Africa", flag: "🇿🇦", currency: "ZAR", currencySymbol: "R", paymentGateway: "stripe" },
  { code: "EG", name: "Egypt", flag: "🇪🇬", currency: "EGP", currencySymbol: "E£", paymentGateway: "local" },
  // Oceania
  { code: "AU", name: "Australia", flag: "🇦🇺", currency: "AUD", currencySymbol: "A$", paymentGateway: "stripe" },
  { code: "NZ", name: "New Zealand", flag: "🇳🇿", currency: "NZD", currencySymbol: "NZ$", paymentGateway: "stripe" },
  // Other
  { code: "OTHER", name: "Other Country", flag: "🌍", currency: "USD", currencySymbol: "$", paymentGateway: "stripe" },
];

// ─────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────

export default function Register() {
  // Step state
  const [step, setStep] = useState(1);

  // Step 1 state — multi-select activities, single tier, single country.
  // Shape mirrors OnboardingCompletePayload (apps/api/app/schemas/onboarding.py).
  const [activities, setActivities] = useState<BusinessActivity[]>([]);
  const [tier, setTier] = useState<BusinessTier | "">("");
  const [country, setCountry] = useState<string>("");
  const [countryDropdownOpen, setCountryDropdownOpen] = useState(false);
  
  // Step 2 state
  const [formData, setFormData] = useState({
    companyName: "",
    contactPerson: "",
    email: "",
    password: "",
    confirmPassword: "",
    agreedToTerms: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  const { toast } = useToast();
  const navigate = useNavigate();
  const { registerWithEmail } = useAuth();

  // ─────────────────────────────────────────────────────────────
  // Auto-detect country from IP (Vercel Geo Headers)
  // ─────────────────────────────────────────────────────────────
  
  useEffect(() => {
    // Only auto-detect if country not already set
    if (country) return;
    
    fetch('/api/geo')
      .then(res => res.json())
      .then(data => {
        if (data.country) {
          // Check if detected country is in our list
          const detectedCountry = COUNTRIES.find(c => c.code === data.country);
          if (detectedCountry) {
            setCountry(data.country);
            console.log(`🌍 Auto-detected country: ${detectedCountry.name} (${detectedCountry.currency})`);
          } else {
            // If country not in list, default to OTHER
            setCountry('OTHER');
            console.log(`🌍 Country ${data.country} not in list, using OTHER`);
          }
        }
      })
      .catch(err => {
        // Silently fail - user can still select manually
        console.log('Geo detection unavailable:', err.message);
      });
  }, []); // Run once on mount

  // ─────────────────────────────────────────────────────────────
  // Role & Business Logic
  // ─────────────────────────────────────────────────────────────

  // Legacy User.role has a CHECK constraint — only exporter/importer/tenant_admin/bank_*
  // are allowed. Enterprise-tier users with an exporter/importer activity get tenant_admin
  // for downstream RBAC; agent/services fall back to exporter (primary activity doesn't
  // matter once Company.business_activities is persisted — routing reads from there).
  const getBackendRole = (): string => {
    if (tier === "enterprise") {
      return "tenant_admin";
    }
    const primary = activities[0];
    if (primary === "importer") return "importer";
    return "exporter";
  };

  const toggleActivity = (value: BusinessActivity) => {
    setActivities((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value],
    );
  };

  // ─────────────────────────────────────────────────────────────
  // Handlers
  // ─────────────────────────────────────────────────────────────

  const handleContinue = () => {
    if (activities.length === 0) {
      toast({
        title: "Select what your business does",
        description: "Pick one or more. You can always change this later.",
        variant: "destructive",
      });
      return;
    }
    if (!tier) {
      toast({
        title: "Select your team size",
        description: "Pick the tier that best matches your team.",
        variant: "destructive",
      });
      return;
    }
    if (!country) {
      toast({
        title: "Select your country",
        description: "Please tell us where your company is based.",
        variant: "destructive",
      });
      return;
    }
    setStep(2);
  };

  // Get selected country details
  const selectedCountry = COUNTRIES.find(c => c.code === country);

  const handleBack = () => {
    setStep(1);
  };

  const handleInputChange = (field: string, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    if (formData.password !== formData.confirmPassword) {
      toast({
        title: "Password mismatch",
        description: "Passwords do not match. Please double-check.",
        variant: "destructive",
      });
      setIsLoading(false);
      return;
    }

    if (!formData.agreedToTerms) {
      toast({
        title: "Almost there!",
        description: "Please agree to the terms before creating an account.",
        variant: "destructive",
      });
      setIsLoading(false);
      return;
    }

    if (!tier) {
      // Guarded by handleContinue on step 1, but TS needs the narrowing.
      toast({
        title: "Select your team size",
        description: "Please complete step 1 before registering.",
        variant: "destructive",
      });
      setIsLoading(false);
      return;
    }

    try {
      const backendRole = getBackendRole();
      const normalizedTier: BusinessTier = tier;

      // Sort activities by canonical priority so two users with the same
      // selections (but different click orders) land on the same dashboard.
      // See ACTIVITY_PRIORITY in @/api/onboarding.
      const sortedActivities = sortActivitiesByPriority(activities);
      const primaryActivity = sortedActivities[0];

      // Register with company info. We still pass legacy fields (companyType/
      // companySize/businessTypes) so registerWithEmail's existing contract
      // stays green until that signature can be simplified in a follow-up.
      await registerWithEmail(
        formData.email,
        formData.password,
        formData.contactPerson,
        backendRole,
        {
          companyName: formData.companyName,
          companyType: primaryActivity,                  // priority-sorted primary
          companySize: normalizedTier,
          businessTypes: sortedActivities,
          country: country,
          currency: selectedCountry?.currency || "USD",
          paymentGateway: selectedCountry?.paymentGateway || "stripe",
        },
      );

      // Persist the 3-question wizard answers into Company.business_activities /
      // Company.tier / Company.country via the new endpoint. If this fails we
      // surface the failure instead of silently landing the user on the default
      // (exporter) dashboard — they need activities=['agent'] (or whatever
      // they picked) to persist, otherwise the WorkspaceSwitcher,
      // EnterpriseGroupLink, and AgencyDashboard read empty defaults.
      try {
        await completeOnboardingRequest({
          activities: sortedActivities,
          country,
          tier: normalizedTier,
          company_name: formData.companyName,
        });
      } catch (error: any) {
        const detail =
          error?.response?.data?.detail ||
          error?.message ||
          "Your account was created but we couldn't save your onboarding answers. Sign in and re-run the wizard from /onboarding.";
        toast({
          title: "Onboarding not fully saved",
          description: detail,
          variant: "destructive",
        });
        // Still navigate — the user's Supabase account exists, and /onboarding
        // status will now return completed=false (after 2026-04-23 backend fix),
        // so the router will redirect them to the wizard on next mount.
      }

      toast({
        title: "Welcome to TRDR Hub! 🎉",
        description: "Your account is ready. You have $100 in free credits!",
      });

      navigate("/lcopilot/dashboard", { replace: true });

    } catch (error: any) {
      const message =
        error?.response?.data?.detail ||
        error?.message ||
        "We couldn't complete your registration. Please try again.";
      toast({
        title: "Registration failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // ─────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────

  return (
    <div className="grid min-h-screen lg:grid-cols-2 bg-[#00261C]">
      {/* Left Column - Registration Form */}
      <div className="relative flex flex-col p-6 md:p-10 overflow-y-auto">
        {/* Background effects */}
        <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-[#B2F273]/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-[#B2F273]/5 rounded-full blur-3xl" />
        
        {/* Header with logo */}
        <div className="flex items-center justify-between relative z-10 mb-8">
          <Link to="/" className="flex items-center gap-2">
            <img 
              src="/logo-dark-v2.png" 
              alt="TRDR Hub" 
              className="h-8 w-auto object-contain"
            />
          </Link>
          
          {/* Progress Indicator */}
          <div className="flex items-center gap-2">
            <div className={cn(
              "flex items-center justify-center w-7 h-7 rounded-full text-xs font-medium transition-colors",
              step >= 1 ? "bg-[#B2F273] text-[#00261C]" : "bg-[#00382E] text-[#EDF5F2]/40"
            )}>
              {step > 1 ? <Check className="w-3.5 h-3.5" /> : "1"}
            </div>
            <div className={cn(
              "w-8 h-0.5 rounded-full transition-colors",
              step >= 2 ? "bg-[#B2F273]" : "bg-[#00382E]"
            )} />
            <div className={cn(
              "flex items-center justify-center w-7 h-7 rounded-full text-xs font-medium transition-colors",
              step >= 2 ? "bg-[#B2F273] text-[#00261C]" : "bg-[#00382E] text-[#EDF5F2]/40"
            )}>
              2
            </div>
          </div>
        </div>
        
        {/* Form container */}
        <div className="flex flex-1 items-center justify-center relative z-10 py-8">
          <div className="w-full max-w-md">
            
            {/* Step 1: Business Context */}
            {step === 1 && (
              <>
                <div className="mb-8 text-center md:text-left">
                  <h1 className="text-3xl font-bold text-white mb-2 font-display">
                    What does your company do?
                  </h1>
                  <p className="text-[#EDF5F2]/60">
                    This helps us personalize your experience
                  </p>
                </div>

                <div className="space-y-6">
                  {/* Business Activities — multi-select */}
                  <div className="space-y-3">
                    <Label className="text-sm font-medium text-[#EDF5F2]/80">
                      Business Activities
                      <span className="ml-1 text-xs text-[#EDF5F2]/40">(select all that apply)</span>
                    </Label>
                    <div className="grid grid-cols-2 gap-3">
                      {COMPANY_TYPES.map((option) => {
                        const Icon = option.icon;
                        const isSelected = activities.includes(option.value);
                        return (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() => toggleActivity(option.value)}
                            className={cn(
                              "relative flex flex-col items-center gap-2 p-4 rounded-xl border transition-all text-center",
                              isSelected 
                                ? "border-[#B2F273] bg-[#B2F273]/10" 
                                : "border-[#EDF5F2]/10 bg-[#00382E]/30 hover:border-[#EDF5F2]/20"
                            )}
                          >
                            {isSelected && (
                              <div className="absolute top-2 right-2">
                                <Check className="w-3.5 h-3.5 text-[#B2F273]" />
                              </div>
                            )}
                            <div className={cn(
                              "w-10 h-10 rounded-lg flex items-center justify-center transition-colors",
                              isSelected ? "bg-[#B2F273]/20" : "bg-[#00382E]"
                            )}>
                              <Icon className={cn(
                                "w-5 h-5 transition-colors",
                                isSelected ? "text-[#B2F273]" : "text-[#EDF5F2]/40"
                              )} />
                            </div>
                            <div>
                              <p className={cn(
                                "font-medium text-sm transition-colors",
                                isSelected ? "text-white" : "text-[#EDF5F2]/80"
                              )}>{option.label}</p>
                              <p className="text-xs text-[#EDF5F2]/40 mt-1">{option.description}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Team Size / Tier */}
                  <div className="space-y-3">
                    <Label className="text-sm font-medium text-[#EDF5F2]/80">Team Size</Label>
                    <div className="grid grid-cols-2 gap-3">
                      {COMPANY_SIZES.map((option) => {
                        const Icon = option.icon;
                        const isSelected = tier === option.value;
                        return (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() => setTier(option.value)}
                            className={cn(
                              "relative flex items-center gap-3 p-3 rounded-xl border transition-all text-left",
                              isSelected 
                                ? "border-[#B2F273] bg-[#B2F273]/10" 
                                : "border-[#EDF5F2]/10 bg-[#00382E]/30 hover:border-[#EDF5F2]/20"
                            )}
                          >
                            {isSelected && (
                              <div className="absolute top-2 right-2">
                                <Check className="w-3.5 h-3.5 text-[#B2F273]" />
                              </div>
                            )}
                            <div className={cn(
                              "w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors",
                              isSelected ? "bg-[#B2F273]/20" : "bg-[#00382E]"
                            )}>
                              <Icon className={cn(
                                "w-4 h-4 transition-colors",
                                isSelected ? "text-[#B2F273]" : "text-[#EDF5F2]/40"
                              )} />
                            </div>
                            <div>
                              <p className={cn(
                                "font-medium text-sm transition-colors",
                                isSelected ? "text-white" : "text-[#EDF5F2]/80"
                              )}>{option.label}</p>
                              <p className="text-xs text-[#EDF5F2]/40">{option.employees}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Country Selection */}
                  <div className="space-y-3">
                    <Label className="text-sm font-medium text-[#EDF5F2]/80">
                      <Globe className="w-4 h-4 inline mr-2" />
                      Where is your company based?
                    </Label>
                    <div className="relative">
                      <button
                        type="button"
                        onClick={() => setCountryDropdownOpen(!countryDropdownOpen)}
                        className={cn(
                          "w-full flex items-center justify-between px-4 py-3 rounded-xl border transition-all text-left",
                          country 
                            ? "border-[#B2F273] bg-[#B2F273]/10" 
                            : "border-[#EDF5F2]/10 bg-[#00382E]/30 hover:border-[#EDF5F2]/20"
                        )}
                      >
                        {selectedCountry ? (
                          <span className="flex items-center gap-2">
                            <span className="text-xl">{selectedCountry.flag}</span>
                            <span className="text-white">{selectedCountry.name}</span>
                            <span className="text-[#EDF5F2]/40 text-sm">({selectedCountry.currency})</span>
                          </span>
                        ) : (
                          <span className="text-[#EDF5F2]/40">Select your country</span>
                        )}
                        <ChevronDown className={cn(
                          "w-4 h-4 text-[#EDF5F2]/40 transition-transform",
                          countryDropdownOpen && "rotate-180"
                        )} />
                      </button>
                      
                      {countryDropdownOpen && (
                        <div className="absolute z-50 mt-2 w-full max-h-60 overflow-y-auto rounded-xl border border-[#EDF5F2]/10 bg-[#00261C] shadow-xl">
                          {COUNTRIES.map((c) => (
                            <button
                              key={c.code}
                              type="button"
                              onClick={() => {
                                setCountry(c.code);
                                setCountryDropdownOpen(false);
                              }}
                              className={cn(
                                "w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-[#00382E] transition-colors",
                                country === c.code && "bg-[#B2F273]/10"
                              )}
                            >
                              <span className="text-xl">{c.flag}</span>
                              <span className={cn(
                                "flex-1",
                                country === c.code ? "text-white" : "text-[#EDF5F2]/80"
                              )}>{c.name}</span>
                              <span className="text-[#EDF5F2]/40 text-sm">{c.currencySymbol}</span>
                              {country === c.code && (
                                <Check className="w-4 h-4 text-[#B2F273]" />
                              )}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    {selectedCountry && selectedCountry.paymentGateway !== "stripe" && (
                      <p className="text-xs text-[#B2F273]">
                        ✓ Local payment options available in {selectedCountry.currency}
                      </p>
                    )}
                  </div>

                  {/* Continue Button */}
                  <Button 
                    onClick={handleContinue}
                    className="w-full h-11 bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-bold rounded-xl"
                  >
                    Continue
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>

                  {/* Bank CTA */}
                  <div className="flex items-center gap-3 p-3 rounded-xl bg-[#00382E]/50 border border-[#EDF5F2]/10">
                    <div className="w-9 h-9 rounded-lg bg-[#B2F273]/10 flex items-center justify-center flex-shrink-0 border border-[#B2F273]/20">
                      <Landmark className="w-4 h-4 text-[#B2F273]" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-[#EDF5F2]">Bank or Financial Institution?</p>
                      <a 
                        href="mailto:enterprise@trdrhub.com?subject=Bank%20Inquiry"
                        className="text-xs text-[#B2F273] hover:text-[#a3e662] inline-flex items-center gap-1 transition-colors"
                      >
                        Contact our enterprise team <ArrowRight className="w-3 h-3" />
                      </a>
                    </div>
                  </div>

                  {/* Login Link */}
                  <p className="text-center text-sm text-[#EDF5F2]/60">
                    Already have an account?{" "}
                    <Link to="/login" className="text-[#B2F273] hover:text-[#a3e662] font-medium">
                      Sign in
                    </Link>
                  </p>
                </div>
              </>
            )}

            {/* Step 2: Account Details */}
            {step === 2 && (
              <>
                <div className="mb-8 text-center md:text-left">
                  <h1 className="text-3xl font-bold text-white mb-2 font-display">
                    Create your account
                  </h1>
                  <p className="text-[#EDF5F2]/60">
                    {activities
                      .map((a) => COMPANY_TYPES.find((t) => t.value === a)?.label ?? a)
                      .join(" & ")}
                    {" • "}
                    {COMPANY_SIZES.find((s) => s.value === tier)?.label} Team
                  </p>
                </div>

                <form onSubmit={handleRegister} className="space-y-4">
                  {/* Company Name */}
                  <div className="space-y-2">
                    <Label htmlFor="companyName" className="text-sm font-medium text-[#EDF5F2]/80">
                      Company Name
                    </Label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#EDF5F2]/40" />
                      <Input
                        id="companyName"
                        placeholder="Your Company Ltd."
                        value={formData.companyName}
                        onChange={(e) => handleInputChange("companyName", e.target.value)}
                        className="pl-10 h-11 bg-[#00382E]/50 border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/30 focus:border-[#B2F273]/50 focus:ring-[#B2F273]/20 rounded-xl"
                        required
                      />
                    </div>
                  </div>

                  {/* Contact Person */}
                  <div className="space-y-2">
                    <Label htmlFor="contactPerson" className="text-sm font-medium text-[#EDF5F2]/80">
                      Your Name
                    </Label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#EDF5F2]/40" />
                      <Input
                        id="contactPerson"
                        placeholder="John Smith"
                        value={formData.contactPerson}
                        onChange={(e) => handleInputChange("contactPerson", e.target.value)}
                        className="pl-10 h-11 bg-[#00382E]/50 border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/30 focus:border-[#B2F273]/50 focus:ring-[#B2F273]/20 rounded-xl"
                        required
                      />
                    </div>
                  </div>

                  {/* Email */}
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-sm font-medium text-[#EDF5F2]/80">
                      Work Email
                    </Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#EDF5F2]/40" />
                      <Input
                        id="email"
                        type="email"
                        placeholder="john@company.com"
                        value={formData.email}
                        onChange={(e) => handleInputChange("email", e.target.value)}
                        className="pl-10 h-11 bg-[#00382E]/50 border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/30 focus:border-[#B2F273]/50 focus:ring-[#B2F273]/20 rounded-xl"
                        required
                      />
                    </div>
                  </div>

                  {/* Password Fields */}
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="password" className="text-sm font-medium text-[#EDF5F2]/80">
                        Password
                      </Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#EDF5F2]/40" />
                        <Input
                          id="password"
                          type={showPassword ? "text" : "password"}
                          placeholder="••••••••"
                          value={formData.password}
                          onChange={(e) => handleInputChange("password", e.target.value)}
                          className="pl-10 pr-10 h-11 bg-[#00382E]/50 border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/30 focus:border-[#B2F273]/50 focus:ring-[#B2F273]/20 rounded-xl"
                          required
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 text-[#EDF5F2]/40 hover:text-white hover:bg-transparent"
                        >
                          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </Button>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="confirmPassword" className="text-sm font-medium text-[#EDF5F2]/80">
                        Confirm
                      </Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#EDF5F2]/40" />
                        <Input
                          id="confirmPassword"
                          type={showConfirmPassword ? "text" : "password"}
                          placeholder="••••••••"
                          value={formData.confirmPassword}
                          onChange={(e) => handleInputChange("confirmPassword", e.target.value)}
                          className="pl-10 pr-10 h-11 bg-[#00382E]/50 border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/30 focus:border-[#B2F273]/50 focus:ring-[#B2F273]/20 rounded-xl"
                          required
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 text-[#EDF5F2]/40 hover:text-white hover:bg-transparent"
                        >
                          {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* Free Credits Banner */}
                  <div className="flex items-center gap-3 p-3 rounded-xl bg-[#B2F273]/10 border border-[#B2F273]/20">
                    <div className="w-9 h-9 rounded-lg bg-[#B2F273]/20 flex items-center justify-center flex-shrink-0">
                      <Gift className="w-4 h-4 text-[#B2F273]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">$100 in free credits</p>
                      <p className="text-xs text-[#B2F273]">No credit card • Use across all tools</p>
                    </div>
                  </div>

                  {/* Terms Checkbox */}
                  <div className="flex items-start gap-3">
                    <Checkbox
                      id="terms"
                      checked={formData.agreedToTerms}
                      onCheckedChange={(checked) => handleInputChange("agreedToTerms", Boolean(checked))}
                      className="mt-0.5 border-[#EDF5F2]/40 data-[state=checked]:bg-[#B2F273] data-[state=checked]:border-[#B2F273]"
                    />
                    <Label htmlFor="terms" className="text-sm text-[#EDF5F2]/60 leading-relaxed">
                      I agree to the{" "}
                      <Link to="/terms" target="_blank" className="text-[#B2F273] hover:underline">
                        Terms
                      </Link>{" "}and{" "}
                      <Link to="/privacy" target="_blank" className="text-[#B2F273] hover:underline">
                        Privacy Policy
                      </Link>
                    </Label>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-3 pt-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleBack}
                      className="flex-1 h-11 border-[#EDF5F2]/10 text-[#EDF5F2]/80 hover:bg-[#00382E] hover:text-white bg-transparent rounded-xl"
                    >
                      <ArrowLeft className="w-4 h-4 mr-2" />
                      Back
                    </Button>
                    <Button 
                      type="submit"
                      disabled={isLoading}
                      className="flex-[2] h-11 bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-bold rounded-xl"
                    >
                      {isLoading ? "Creating..." : "Create Account"}
                    </Button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="absolute bottom-6 left-0 right-0 flex items-center justify-center gap-6 text-xs text-[#EDF5F2]/40">
          <Link to="/terms" className="hover:text-white transition-colors">Terms</Link>
          <Link to="/privacy" className="hover:text-white transition-colors">Privacy</Link>
          <Link to="/contact" className="hover:text-white transition-colors">Contact</Link>
        </div>
      </div>

      {/* Right Column - Feature showcase */}
      <div className="relative hidden lg:flex flex-col justify-center p-12 overflow-hidden bg-[#001E16]">
        {/* Background image */}
        <div 
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-20 mix-blend-luminosity"
          style={{ 
            backgroundImage: `url('https://images.unsplash.com/photo-1494412574643-ff11b0a5c1c3?q=80&w=2070&auto=format&fit=crop')`,
          }}
        />
        
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:48px_48px]" />
        
        {/* Gradient orbs */}
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-[#B2F273]/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/3 left-1/4 w-64 h-64 bg-[#B2F273]/5 rounded-full blur-3xl animate-pulse delay-700" />
        
        <div className="relative z-10 max-w-lg">
          {/* Headline */}
          <h2 className="text-4xl font-bold text-white mb-6 leading-tight font-display">
            Everything Trade.
            <br />
            <span className="text-[#B2F273] text-glow-sm">
              One Platform.
            </span>
          </h2>
          
          <p className="text-[#EDF5F2]/60 text-lg mb-12 font-light">
            Join thousands of traders who validate documents, verify prices, and manage compliance in one place.
          </p>

          {/* Features list */}
          <div className="space-y-4 mb-12">
            {FEATURES.map((feature) => {
              const Icon = feature.icon;
              return (
                <div 
                  key={feature.label}
                  className="flex items-center gap-4 p-4 rounded-xl bg-[#00382E]/50 border border-[#EDF5F2]/10 backdrop-blur-sm"
                >
                  <div className="w-12 h-12 rounded-xl bg-[#B2F273]/10 flex items-center justify-center shrink-0">
                    <Icon className="w-6 h-6 text-[#B2F273]" />
                  </div>
                  <div>
                    <p className="font-medium text-white">{feature.label}</p>
                    <p className="text-sm text-[#EDF5F2]/60">{feature.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Stats */}
          <div className="flex items-center gap-8 border-t border-[#EDF5F2]/10 pt-8">
            <div>
              <div className="text-3xl font-bold text-white font-display">3.5k+</div>
              <div className="text-sm text-[#EDF5F2]/40 font-mono uppercase tracking-wider mt-1">Rules</div>
            </div>
            <div className="w-px h-12 bg-[#EDF5F2]/10" />
            <div>
              <div className="text-3xl font-bold text-white font-display">60+</div>
              <div className="text-sm text-[#EDF5F2]/40 font-mono uppercase tracking-wider mt-1">Countries</div>
            </div>
            <div className="w-px h-12 bg-[#EDF5F2]/10" />
            <div>
              <div className="text-3xl font-bold text-white font-display">99.9%</div>
              <div className="text-sm text-[#EDF5F2]/40 font-mono uppercase tracking-wider mt-1">Uptime</div>
            </div>
          </div>
        </div>

        {/* Trust badges */}
        <div className="absolute bottom-8 left-12 right-12 flex items-center justify-between text-xs text-[#EDF5F2]/40 font-mono uppercase tracking-widest">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-[#B2F273] rounded-full" />
            SOC2 Aligned
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-[#B2F273] rounded-full" />
            Bank Approved
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-[#B2F273] rounded-full" />
            UCP600 Compliant
          </div>
        </div>
      </div>
    </div>
  );
}
