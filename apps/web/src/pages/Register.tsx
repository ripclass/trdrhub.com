import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useOnboarding } from "@/hooks/use-onboarding";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────────────────────
// Types & Constants
// ─────────────────────────────────────────────────────────────

type CompanyType = "exporter" | "importer" | "both" | "logistics" | "";
type CompanySize = "small" | "growing" | "established" | "enterprise" | "";

interface CompanyTypeOption {
  value: CompanyType;
  label: string;
  description: string;
  icon: React.ElementType;
}

interface CompanySizeOption {
  value: CompanySize;
  label: string;
  employees: string;
  icon: React.ElementType;
}

const COMPANY_TYPES: CompanyTypeOption[] = [
  { 
    value: "exporter", 
    label: "Exporter", 
    description: "We export goods internationally",
    icon: Package,
  },
  { 
    value: "importer", 
    label: "Importer", 
    description: "We import goods into our country",
    icon: PackageOpen,
  },
  { 
    value: "both", 
    label: "Both", 
    description: "We do import and export",
    icon: RefreshCw,
  },
  { 
    value: "logistics", 
    label: "Logistics", 
    description: "Freight forwarding & logistics",
    icon: Truck,
  },
];

const COMPANY_SIZES: CompanySizeOption[] = [
  { 
    value: "small", 
    label: "Small", 
    employees: "1-20 people",
    icon: User,
  },
  { 
    value: "growing", 
    label: "Growing", 
    employees: "21-100 people",
    icon: Users,
  },
  { 
    value: "established", 
    label: "Established", 
    employees: "100-500 people",
    icon: Building,
  },
  { 
    value: "enterprise", 
    label: "Enterprise", 
    employees: "500+ people",
    icon: Factory,
  },
];

// ─────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────

export default function Register() {
  // Step state
  const [step, setStep] = useState(1);
  
  // Step 1 state
  const [companyType, setCompanyType] = useState<CompanyType>("");
  const [companySize, setCompanySize] = useState<CompanySize>("");
  
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
  const { updateProgress } = useOnboarding();

  // ─────────────────────────────────────────────────────────────
  // Role & Business Logic
  // ─────────────────────────────────────────────────────────────

  const getBackendRole = (type: CompanyType, size: CompanySize): string => {
    // Large companies get tenant_admin regardless of type
    if (size === "established" || size === "enterprise") {
      return "tenant_admin";
    }
    
    // Small/growing companies get role based on type
    const roleMap: Record<string, string> = {
      exporter: "exporter",
      importer: "importer",
      both: "exporter",      // SME "both" defaults to exporter
      logistics: "exporter", // Logistics uses exporter flow
    };

    return roleMap[type] || "exporter";
  };

  const getBusinessTypes = (type: CompanyType): string[] => {
    if (type === "both") {
      return ["exporter", "importer"];
    }
    if (type === "logistics") {
      return ["exporter"]; // Backend recognizes exporter
    }
    return type ? [type] : [];
  };

  const mapSizeToBackend = (size: CompanySize): string => {
    const sizeMap: Record<CompanySize, string> = {
      small: "sme",
      growing: "medium",
      established: "large",
      enterprise: "enterprise",
      "": "sme",
    };
    return sizeMap[size];
  };

  // ─────────────────────────────────────────────────────────────
  // Handlers
  // ─────────────────────────────────────────────────────────────

  const handleContinue = () => {
    if (!companyType) {
      toast({
        title: "Select your business type",
        description: "Please tell us what your company does.",
        variant: "destructive",
      });
      return;
    }
    if (!companySize) {
      toast({
        title: "Select your team size",
        description: "Please tell us how big your team is.",
        variant: "destructive",
      });
      return;
    }
    setStep(2);
  };

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

    try {
      const backendRole = getBackendRole(companyType, companySize);
      const businessTypes = getBusinessTypes(companyType);
      const normalizedSize = mapSizeToBackend(companySize);

      // Register with company info
      await registerWithEmail(
        formData.email,
        formData.password,
        formData.contactPerson,
        backendRole,
        {
          companyName: formData.companyName,
          companyType: companyType,
          companySize: normalizedSize,
          businessTypes: businessTypes,
        }
      );

      // Update onboarding progress
      try {
        const requiresTeamSetup = backendRole === "tenant_admin";

        await updateProgress({
          role: backendRole,
          company: {
            name: formData.companyName,
            type: companyType,
            size: normalizedSize,
          },
          business_types: businessTypes,
          complete: !requiresTeamSetup,
          onboarding_step: requiresTeamSetup ? "team_setup" : null,
        });
      } catch (error) {
        console.warn("Failed to sync onboarding progress (non-critical):", error);
      }

      toast({
        title: "Welcome to TRDR Hub! 🎉",
        description: "Your account is ready. You have $100 in free credits!",
      });

      navigate("/hub");

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
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="mx-auto flex min-h-screen max-w-2xl flex-col px-4 py-8 lg:py-12">
        
        {/* Header */}
        <header className="mb-8 text-center">
          <Link to="/" className="inline-flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">TRDR Hub</span>
          </Link>
          
          {/* Progress Indicator */}
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className={cn(
              "flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-colors",
              step >= 1 ? "bg-blue-500 text-white" : "bg-slate-700 text-slate-400"
            )}>
              {step > 1 ? <Check className="w-4 h-4" /> : "1"}
            </div>
            <div className={cn(
              "w-16 h-1 rounded-full transition-colors",
              step >= 2 ? "bg-blue-500" : "bg-slate-700"
            )} />
            <div className={cn(
              "flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-colors",
              step >= 2 ? "bg-blue-500 text-white" : "bg-slate-700 text-slate-400"
            )}>
              2
            </div>
          </div>
          
          <p className="text-sm text-slate-400">
            Step {step} of 2 • {step === 1 ? "Tell us about your business" : "Create your account"}
          </p>
        </header>

        {/* Step 1: Business Context */}
        {step === 1 && (
          <Card className="border-slate-800 bg-slate-900/50 backdrop-blur">
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-2xl text-white">What does your company do?</CardTitle>
              <CardDescription className="text-slate-400">
                This helps us personalize your experience
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              
              {/* Company Type Selection */}
              <div className="space-y-3">
                <Label className="text-sm font-medium text-slate-300">Business Type</Label>
                <div className="grid grid-cols-2 gap-3">
                  {COMPANY_TYPES.map((option) => {
                    const Icon = option.icon;
                    const isSelected = companyType === option.value;
                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setCompanyType(option.value)}
                        className={cn(
                          "relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                          isSelected 
                            ? "border-blue-500 bg-blue-500/10" 
                            : "border-slate-700 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800"
                        )}
                      >
                        {isSelected && (
                          <div className="absolute top-2 right-2">
                            <Check className="w-4 h-4 text-blue-400" />
                          </div>
                        )}
                        <div className={cn(
                          "w-12 h-12 rounded-xl flex items-center justify-center",
                          isSelected ? "bg-blue-500/20" : "bg-slate-700"
                        )}>
                          <Icon className={cn(
                            "w-6 h-6",
                            isSelected ? "text-blue-400" : "text-slate-400"
                          )} />
                        </div>
                        <div className="text-center">
                          <p className={cn(
                            "font-medium",
                            isSelected ? "text-white" : "text-slate-300"
                          )}>{option.label}</p>
                          <p className="text-xs text-slate-500">{option.description}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Company Size Selection */}
              <div className="space-y-3">
                <Label className="text-sm font-medium text-slate-300">Team Size</Label>
                <div className="grid grid-cols-2 gap-3">
                  {COMPANY_SIZES.map((option) => {
                    const Icon = option.icon;
                    const isSelected = companySize === option.value;
                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setCompanySize(option.value)}
                        className={cn(
                          "relative flex items-center gap-3 p-4 rounded-xl border-2 transition-all text-left",
                          isSelected 
                            ? "border-emerald-500 bg-emerald-500/10" 
                            : "border-slate-700 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800"
                        )}
                      >
                        {isSelected && (
                          <div className="absolute top-2 right-2">
                            <Check className="w-4 h-4 text-emerald-400" />
                          </div>
                        )}
                        <div className={cn(
                          "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0",
                          isSelected ? "bg-emerald-500/20" : "bg-slate-700"
                        )}>
                          <Icon className={cn(
                            "w-5 h-5",
                            isSelected ? "text-emerald-400" : "text-slate-400"
                          )} />
                        </div>
                        <div>
                          <p className={cn(
                            "font-medium",
                            isSelected ? "text-white" : "text-slate-300"
                          )}>{option.label}</p>
                          <p className="text-xs text-slate-500">{option.employees}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Continue Button */}
              <Button 
                onClick={handleContinue}
                className="w-full h-12 bg-gradient-to-r from-blue-500 to-emerald-500 hover:from-blue-600 hover:to-emerald-600 text-white font-medium"
              >
                Continue
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>

              {/* Bank CTA */}
              <div className="pt-4 border-t border-slate-800">
                <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                    <Landmark className="w-5 h-5 text-amber-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-amber-200">Bank or Financial Institution?</p>
                    <a 
                      href="mailto:enterprise@trdrhub.com?subject=Bank%20Inquiry"
                      className="text-xs text-amber-400 hover:text-amber-300 inline-flex items-center gap-1"
                    >
                      Contact our enterprise team <ArrowRight className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </div>

              {/* Login Link */}
              <p className="text-center text-sm text-slate-400">
                Already have an account?{" "}
                <Link to="/login" className="text-blue-400 hover:text-blue-300 font-medium">
                  Sign in
                </Link>
              </p>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Account Details */}
        {step === 2 && (
          <Card className="border-slate-800 bg-slate-900/50 backdrop-blur">
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-2xl text-white">Create your account</CardTitle>
              <CardDescription className="text-slate-400">
                {companyType === "both" ? "Exporter & Importer" : COMPANY_TYPES.find(t => t.value === companyType)?.label} • {COMPANY_SIZES.find(s => s.value === companySize)?.label} Team
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleRegister} className="space-y-5">
                
                {/* Company Name */}
                <div className="space-y-2">
                  <Label htmlFor="companyName" className="text-slate-300">Company Name</Label>
                  <div className="relative">
                    <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <Input
                      id="companyName"
                      placeholder="Your Company Ltd."
                      value={formData.companyName}
                      onChange={(e) => handleInputChange("companyName", e.target.value)}
                      className="pl-10 bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500"
                      required
                    />
                  </div>
                </div>

                {/* Contact Person */}
                <div className="space-y-2">
                  <Label htmlFor="contactPerson" className="text-slate-300">Your Name</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <Input
                      id="contactPerson"
                      placeholder="John Smith"
                      value={formData.contactPerson}
                      onChange={(e) => handleInputChange("contactPerson", e.target.value)}
                      className="pl-10 bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500"
                      required
                    />
                  </div>
                </div>

                {/* Email */}
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-slate-300">Work Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="john@company.com"
                      value={formData.email}
                      onChange={(e) => handleInputChange("email", e.target.value)}
                      className="pl-10 bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500"
                      required
                    />
                  </div>
                </div>

                {/* Password Fields */}
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-slate-300">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                      <Input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        placeholder="••••••••"
                        value={formData.password}
                        onChange={(e) => handleInputChange("password", e.target.value)}
                        className="pl-10 pr-10 bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500"
                        required
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 text-slate-500 hover:text-slate-300"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword" className="text-slate-300">Confirm</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                      <Input
                        id="confirmPassword"
                        type={showConfirmPassword ? "text" : "password"}
                        placeholder="••••••••"
                        value={formData.confirmPassword}
                        onChange={(e) => handleInputChange("confirmPassword", e.target.value)}
                        className="pl-10 pr-10 bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500"
                        required
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 text-slate-500 hover:text-slate-300"
                      >
                        {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Free Credits Banner */}
                <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                    <Gift className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-emerald-200">Start with $100 in free credits</p>
                    <p className="text-xs text-emerald-400">No credit card required • Use across all tools</p>
                  </div>
                </div>

                {/* Terms Checkbox */}
                <div className="flex items-start gap-3">
                  <Checkbox
                    id="terms"
                    checked={formData.agreedToTerms}
                    onCheckedChange={(checked) => handleInputChange("agreedToTerms", Boolean(checked))}
                    className="mt-0.5 border-slate-600 data-[state=checked]:bg-blue-500"
                  />
                  <Label htmlFor="terms" className="text-sm text-slate-400 leading-relaxed">
                    I agree to the{" "}
                    <a href="/legal/terms" target="_blank" className="text-blue-400 hover:underline">
                      Terms of Service
                    </a>{" "}and{" "}
                    <a href="/legal/privacy" target="_blank" className="text-blue-400 hover:underline">
                      Privacy Policy
                    </a>
                  </Label>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleBack}
                    className="flex-1 h-12 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back
                  </Button>
                  <Button 
                    type="submit"
                    disabled={isLoading}
                    className="flex-[2] h-12 bg-gradient-to-r from-blue-500 to-emerald-500 hover:from-blue-600 hover:to-emerald-600 text-white font-medium"
                  >
                    {isLoading ? "Creating account..." : "Create Free Account"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <footer className="mt-8 text-center text-xs text-slate-500">
          <div className="flex items-center justify-center gap-4">
            <span>✓ SOC2 Aligned</span>
            <span>✓ 99.9% Uptime</span>
            <span>✓ Bank Approved</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
