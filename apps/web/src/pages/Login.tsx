import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { FileText, Eye, EyeOff, Mail, Lock } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { getOnboardingStatus } from "@/api/onboarding";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();
  const { loginWithEmail } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const profile = await loginWithEmail(email, password);
      toast({
        title: "Login Successful",
        description: "Welcome back to LCopilot!",
      });

      // Get onboarding status FIRST to determine correct dashboard
      // This is critical for "both" exporter/importer users who have role "exporter"
      let destination = "/lcopilot/exporter-dashboard";
      
      try {
        const status = await Promise.race([
          getOnboardingStatus(),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 3000))
        ]) as any;
        
        if (status) {
          const backendRole = status.role;
          const details = status.details as Record<string, any> | undefined;
          const businessTypes = Array.isArray(details?.business_types) ? details?.business_types : [];
          const hasBoth = businessTypes.includes("exporter") && businessTypes.includes("importer");
          const companySize = details?.company?.size;
          const companyType = details?.company?.type;
          
          // Debug logging
          console.log("🔍 Login routing check:", {
            backendRole,
            businessTypes,
            hasBoth,
            companySize,
            companyType,
            company_id: status.company_id,
            completed: status.completed,
            details: details
          });
          
          // Determine destination based on onboarding data
          if (backendRole === "bank_officer" || backendRole === "bank_admin") {
            destination = "/lcopilot/bank-dashboard";
          } else if (backendRole === "tenant_admin") {
            destination = "/lcopilot/enterprise-dashboard";
          } else if (hasBoth && companySize === "sme") {
            // SME "both" users → CombinedDashboard (unified view)
            destination = "/lcopilot/combined-dashboard";
            console.log("✅ Routing to CombinedDashboard (SME both)");
          } else if (hasBoth && (companySize === "medium" || companySize === "large")) {
            // Medium/Large "both" users → EnterpriseDashboard
            destination = "/lcopilot/enterprise-dashboard";
            console.log("✅ Routing to EnterpriseDashboard (Medium/Large both)");
          } else if (companyType === "both" && companySize === "sme") {
            // Fallback: Check company.type directly if business_types not set
            destination = "/lcopilot/combined-dashboard";
            console.log("✅ Routing to CombinedDashboard (fallback: company.type='both', SME)");
          } else if (companyType === "both" && (companySize === "medium" || companySize === "large")) {
            // Fallback: Check company.type directly if business_types not set
            destination = "/lcopilot/enterprise-dashboard";
            console.log("✅ Routing to EnterpriseDashboard (fallback: company.type='both', Medium/Large)");
          } else if (profile.role === "importer") {
            destination = "/lcopilot/importer-dashboard";
          } else if (profile.role === "bank" || profile.role === "bank_officer" || profile.role === "bank_admin") {
            destination = "/lcopilot/bank-dashboard";
          } else {
            console.log("⚠️ No match found, defaulting to exporter-dashboard");
          }
          
          console.log("📍 Final destination:", destination);
        }
      } catch (err) {
        console.warn("Onboarding status check failed or timed out:", err);
        // Fallback to role-based routing if onboarding status unavailable
        if (profile.role === "bank" || profile.role === "bank_officer" || profile.role === "bank_admin") {
          destination = "/lcopilot/bank-dashboard";
        } else if (profile.role === "tenant_admin") {
          destination = "/lcopilot/enterprise-dashboard";
        } else if (profile.role === "importer") {
          destination = "/lcopilot/importer-dashboard";
        }
      }
      
      setIsLoading(false); // Clear loading state before navigation
      navigate(destination);
    } catch (error: any) {
      const message = error?.message || "Please check your credentials and try again.";
      toast({
        title: "Login Failed",
        description: message,
        variant: "destructive",
      });
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-secondary/20 to-primary/5 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="bg-gradient-primary p-3 rounded-xl shadow-medium">
              <FileText className="w-8 h-8 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">LCopilot</h1>
              <p className="text-sm text-muted-foreground">Document Validator</p>
            </div>
          </div>
          <p className="text-muted-foreground">Sign in to validate your LC documents</p>
        </div>

        <Card className="shadow-strong border-0">
          <CardHeader className="space-y-2 text-center">
            <CardTitle className="text-xl">Welcome Back</CardTitle>
            <CardDescription>Enter your credentials to access your dashboard</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium">
                  Email Address
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="your@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-10"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10 pr-10"
                    required
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                    onClick={() => setShowPassword((prev) => !prev)}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <Eye className="w-4 h-4 text-muted-foreground" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <Link to="/forgot-password" className="text-sm text-primary hover:underline">
                  Forgot password?
                </Link>
              </div>

              <Button type="submit" className="w-full bg-gradient-primary hover:opacity-90" disabled={isLoading}>
                {isLoading ? "Signing in..." : "Sign In"}
              </Button>
            </form>

            <div className="mt-6 text-center text-sm text-muted-foreground">
              Don't have an account?{" "}
              <Link to="/register" className="text-primary hover:underline font-medium">
                Create account
              </Link>
            </div>
          </CardContent>
        </Card>

        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-success rounded-full" />
              500+ Exporters
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-success rounded-full" />
              99.2% Uptime
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-success rounded-full" />
              Bank Approved
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}