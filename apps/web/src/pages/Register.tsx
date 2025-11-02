import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { FileText, ShieldCheck, Timer, Sparkles, Building, User, Mail, Lock, Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useOnboarding } from "@/hooks/use-onboarding";
import type { Role } from "@/types/analytics";

const COMPANY_TYPES = [
  { value: "exporter", label: "Exporter" },
  { value: "importer", label: "Importer" },
  { value: "both", label: "Both Exporter & Importer" },
  { value: "bank", label: "Bank / FI" },
  { value: "consultant", label: "Trade Consultant" },
];

export default function Register() {
  const [formData, setFormData] = useState({
    companyName: "",
    contactPerson: "",
    email: "",
    password: "",
    confirmPassword: "",
    companyType: "",
    agreedToTerms: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();
  const { registerWithEmail } = useAuth();
  const { updateProgress } = useOnboarding();

  const routeForRole = (role: Role): string => {
    switch (role) {
      case "admin":
        return "/admin";
      case "bank":
      case "exporter":
      case "importer":
        return "/dashboard";
      default:
        return "/dashboard";
    }
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
      const roleMap: Record<string, string> = {
        exporter: "exporter",
        importer: "importer",
        both: "exporter",
        bank: "bank_officer",
        consultant: "exporter",
      };
      const backendRole = roleMap[formData.companyType] || "exporter";

      const profile = await registerWithEmail(
        formData.email,
        formData.password,
        formData.contactPerson,
        backendRole
      );

      try {
        await updateProgress({ role: backendRole });
      } catch (error) {
        console.warn("Failed to sync onboarding role", error);
      }

      toast({
        title: "Welcome to LCopilot",
        description: "Your account is ready. We’re tailoring the workspace for you…",
      });
      navigate(routeForRole(profile.role));
    } catch (error: any) {
      const message =
        error?.response?.data?.detail ||
        error?.message ||
        "We couldn’t complete your registration. Please try again.";
      toast({
        title: "Registration failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-secondary/10 to-primary/5">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-12 lg:px-8">
        <header className="mb-10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-primary px-3 py-2 shadow-md">
              <FileText className="h-7 w-7 text-primary-foreground" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-primary">LC Document Copilot</p>
              <h1 className="text-xl font-semibold text-foreground">Create your LCopilot workspace</h1>
            </div>
          </div>
          <div className="hidden text-sm text-muted-foreground md:block">
            Already onboard? {""}
            <Link to="/login" className="font-medium text-primary hover:underline">
              Sign in
            </Link>
          </div>
        </header>

        <div className="grid flex-1 gap-10 lg:grid-cols-12">
          <div className="flex flex-col justify-between rounded-3xl bg-card/60 p-8 shadow-strong backdrop-blur lg:col-span-5">
            <div className="space-y-6">
              <div className="rounded-2xl bg-gradient-to-br from-primary to-primary/70 p-6 text-primary-foreground shadow-lg">
                <p className="text-sm uppercase tracking-wide opacity-80">Onboarding in minutes</p>
                <h2 className="mt-2 text-2xl font-semibold">Designed for trade and treasury teams</h2>
                <p className="mt-3 text-sm opacity-80">
                  LCopilot connects Supabase authentication with our progressive onboarding flow so you can invite
                  teams, capture KYC details, and start validating documents without custom integrations.
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-start gap-3 rounded-xl border border-primary/20 bg-background/70 p-4 shadow-sm">
                  <ShieldCheck className="mt-1 h-5 w-5 text-primary" />
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Enterprise-grade security</h3>
                    <p className="text-sm text-muted-foreground">
                      Supabase Auth manages credentials, while our backend enforces role-based onboarding and KYC checkpoints.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-xl border border-primary/20 bg-background/70 p-4 shadow-sm">
                  <Timer className="mt-1 h-5 w-5 text-primary" />
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Go live in two minutes</h3>
                    <p className="text-sm text-muted-foreground">
                      Guided onboarding walks each role through the essentials—exporters, importers, and banks get tailored experiences.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-xl border border-primary/20 bg-background/70 p-4 shadow-sm">
                  <Sparkles className="mt-1 h-5 w-5 text-primary" />
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Automations built-in</h3>
                    <p className="text-sm text-muted-foreground">
                      Your workspace instantly links to verification services, document AI, and compliance reporting.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 space-y-2 text-xs text-muted-foreground">
              <p>Trusted by export houses across APAC</p>
              <Separator className="opacity-30" />
              <div className="flex flex-wrap gap-4">
                <span>✔ Free trial</span>
                <span>✔ No credit card</span>
                <span>✔ SOC2-aligned controls</span>
              </div>
            </div>
          </div>

          <Card className="relative border-0 shadow-strong lg:col-span-7">
            <CardHeader className="space-y-1">
              <CardTitle className="text-xl">Create your account</CardTitle>
              <CardDescription>
                Tell us a little about your company so we can personalise onboarding and document validation flows.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleRegister} className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="companyName">Company name</Label>
                    <div className="relative">
                      <Building className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="companyName"
                        placeholder="Your Export Company Ltd."
                        value={formData.companyName}
                        onChange={(e) => handleInputChange("companyName", e.target.value)}
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="contactPerson">Contact person</Label>
                    <div className="relative">
                      <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="contactPerson"
                        placeholder="Your full name"
                        value={formData.contactPerson}
                        onChange={(e) => handleInputChange("contactPerson", e.target.value)}
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">Business email</Label>
                    <div className="relative">
                      <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="email"
                        type="email"
                        placeholder="contact@yourcompany.com"
                        value={formData.email}
                        onChange={(e) => handleInputChange("email", e.target.value)}
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="companyType">Company type</Label>
                    <Select
                      value={formData.companyType}
                      onValueChange={(value) => handleInputChange("companyType", value)}
                      required
                    >
                      <SelectTrigger className="h-11">
                        <SelectValue placeholder="Select your business type" />
                      </SelectTrigger>
                      <SelectContent>
                        {COMPANY_TYPES.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <div className="relative">
                      <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        placeholder="Create a strong password"
                        value={formData.password}
                        onChange={(e) => handleInputChange("password", e.target.value)}
                        className="pl-10 pr-12"
                        required
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowPassword((prev) => !prev)}
                        className="absolute right-1 top-1/2 h-8 w-8 -translate-y-1/2 text-muted-foreground"
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Use 12+ characters with a mix of letters, numbers, and symbols.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm password</Label>
                    <div className="relative">
                      <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="confirmPassword"
                        type={showConfirmPassword ? "text" : "password"}
                        placeholder="Confirm your password"
                        value={formData.confirmPassword}
                        onChange={(e) => handleInputChange("confirmPassword", e.target.value)}
                        className="pl-10 pr-12"
                        required
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowConfirmPassword((prev) => !prev)}
                        className="absolute right-1 top-1/2 h-8 w-8 -translate-y-1/2 text-muted-foreground"
                      >
                        {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl bg-muted/50 p-4 text-sm">
                  <h4 className="font-medium text-foreground">What happens next?</h4>
                  <ul className="mt-2 space-y-1 text-muted-foreground">
                    <li>• We’ll send a verification email through Supabase Auth.</li>
                    <li>• Complete your role-specific onboarding checklist.</li>
                    <li>• Invite teammates and connect to Document AI / analytics modules.</li>
                  </ul>
                </div>

                <div className="flex items-start gap-3">
                  <Checkbox
                    id="terms"
                    checked={formData.agreedToTerms}
                    onCheckedChange={(checked) => handleInputChange("agreedToTerms", Boolean(checked))}
                  />
                  <Label htmlFor="terms" className="text-sm text-muted-foreground">
                    I agree to the {""}
                    <a href="/legal/terms" target="_blank" rel="noopener" className="text-primary underline">
                      Terms of Service
                    </a>{" "}and {""}
                    <a href="/legal/privacy" target="_blank" rel="noopener" className="text-primary underline">
                      Privacy Policy
                    </a>
                  </Label>
                </div>

                <Button type="submit" className="w-full bg-gradient-primary hover:opacity-90" disabled={isLoading}>
                  {isLoading ? "Creating workspace..." : "Create your workspace"}
                </Button>

                <p className="text-center text-sm text-muted-foreground lg:hidden">
                  Already have an account? {""}
                  <Link to="/login" className="font-medium text-primary hover:underline">
                    Sign in
                  </Link>
                </p>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}