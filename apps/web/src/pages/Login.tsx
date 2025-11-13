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
      let status: any = null;
      
      try {
        status = await Promise.race([
          getOnboardingStatus(),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 3000))
        ]) as any;
        
        if (status) {
          const backendRole = status.role;
          const details = status.details as Record<string, any> | undefined;
          
          // Check multiple sources for business types
          const businessTypes = Array.isArray(details?.business_types) ? details.business_types : [];
          const companyType = details?.company?.type;
          const companySize = details?.company?.size;
          
          // Check if user is "both" exporter/importer from multiple sources
          const hasBothBusinessTypes = businessTypes.includes("exporter") && businessTypes.includes("importer");
          const isCompanyTypeBoth = companyType === "both" || 
                                    companyType === "Both Exporter & Importer" ||
                                    companyType === "both_exporter_importer";
          
          // More robust check: if company type is "both" but business_types not set, infer it
          const isCombinedUser = hasBothBusinessTypes || isCompanyTypeBoth;
          
          // If company type is "both" but business_types not set, set it for routing
          if (isCompanyTypeBoth && !hasBothBusinessTypes) {
            console.log("ℹ️ Detected company_type='both' but business_types not set, inferring combined user");
          }
          
          // Debug logging
          console.log("🔍 Login routing check:", {
            backendRole,
            businessTypes,
            hasBothBusinessTypes,
            isCompanyTypeBoth,
            isCombinedUser,
            companySize,
            companyType,
            company_id: status.company_id,
            completed: status.completed,
            profileRole: profile.role,
            details: details
          });
          
          // Determine destination based on onboarding data
          if (backendRole === "bank_officer" || backendRole === "bank_admin") {
            destination = "/lcopilot/bank-dashboard";
            console.log("✅ Routing to BankDashboard");
          } else if (backendRole === "tenant_admin") {
            destination = "/lcopilot/enterprise-dashboard";
            console.log("✅ Routing to EnterpriseDashboard (tenant_admin)");
          } else if (isCombinedUser) {
            // Combined users routing based on company size
            if (companySize === "sme" || !companySize) {
              // SME "both" users OR no size specified → CombinedDashboard (unified view)
              // Default to SME/CombinedDashboard if size is missing
              destination = "/lcopilot/combined-dashboard";
              console.log(`✅ Routing to CombinedDashboard (${companySize || 'default SME'} both user)`);
            } else if (companySize === "medium" || companySize === "large") {
              // Medium/Large "both" users → EnterpriseDashboard
              destination = "/lcopilot/enterprise-dashboard";
              console.log("✅ Routing to EnterpriseDashboard (Medium/Large both)");
            } else {
              // Unknown size, default to CombinedDashboard for SME
              destination = "/lcopilot/combined-dashboard";
              console.log("✅ Routing to CombinedDashboard (both user, unknown size - defaulting to SME)");
            }
          } else if (profile.role === "importer") {
            destination = "/lcopilot/importer-dashboard";
            console.log("✅ Routing to ImporterDashboard");
          } else if (profile.role === "bank" || profile.role === "bank_officer" || profile.role === "bank_admin") {
            destination = "/lcopilot/bank-dashboard";
            console.log("✅ Routing to BankDashboard (profile role)");
          } else {
            console.log("⚠️ No match found, defaulting to exporter-dashboard");
          }
          
          console.log("📍 Final destination:", destination);
        }
      } catch (err) {
        console.warn("Onboarding status check failed or timed out:", err);
        console.warn("Error details:", err);
        
        // Fallback: Try to check user profile for company info
        // Sometimes onboarding status might fail but we can still check profile
        try {
          const profileCompanyType = (profile as any).company_type || (profile as any).companyType;
          const profileBusinessTypes = (profile as any).business_types || (profile as any).businessTypes;
          
          if (profileCompanyType === "both" || profileCompanyType === "Both Exporter & Importer") {
            destination = "/lcopilot/combined-dashboard";
            console.log("✅ Fallback: Routing to CombinedDashboard (from profile company_type)");
          } else if (Array.isArray(profileBusinessTypes) && 
                     profileBusinessTypes.includes("exporter") && 
                     profileBusinessTypes.includes("importer")) {
            destination = "/lcopilot/combined-dashboard";
            console.log("✅ Fallback: Routing to CombinedDashboard (from profile business_types)");
          }
        } catch (profileErr) {
          console.warn("Could not check profile for company info:", profileErr);
        }
        
        // Final fallback to role-based routing if onboarding status unavailable
        if (destination === "/lcopilot/exporter-dashboard") {
          if (profile.role === "bank" || profile.role === "bank_officer" || profile.role === "bank_admin") {
            destination = "/lcopilot/bank-dashboard";
          } else if (profile.role === "tenant_admin") {
            destination = "/lcopilot/enterprise-dashboard";
          } else if (profile.role === "importer") {
            destination = "/lcopilot/importer-dashboard";
          }
        }
      }
      
      // CRITICAL: If onboarding status returned empty details, retry once after a short delay
      // This gives the backend time to restore data from company record
      if (status && (!status.details || Object.keys(status.details).length === 0) && !status.company_id) {
        console.log("⚠️ Onboarding data is empty, retrying status check after delay...");
        try {
          // Wait a bit for backend to potentially restore data
          await new Promise(resolve => setTimeout(resolve, 1000));
          const retryStatus = await Promise.race([
            getOnboardingStatus(),
            new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 2000))
          ]) as any;
          
          if (retryStatus && (retryStatus.details && Object.keys(retryStatus.details).length > 0 || retryStatus.company_id)) {
            console.log("✅ Retry successful, re-evaluating routing...");
            const retryDetails = retryStatus.details as Record<string, any> | undefined;
            const retryBusinessTypes = Array.isArray(retryDetails?.business_types) ? retryDetails.business_types : [];
            const retryCompanyType = retryDetails?.company?.type;
            const retryCompanySize = retryDetails?.company?.size;
            const retryHasBoth = retryBusinessTypes.includes("exporter") && retryBusinessTypes.includes("importer");
            const retryIsCompanyTypeBoth = retryCompanyType === "both" || retryCompanyType === "Both Exporter & Importer";
            const retryIsCombinedUser = retryHasBoth || retryIsCompanyTypeBoth;
            
            if (retryIsCombinedUser) {
              if (retryCompanySize === "sme" || !retryCompanySize) {
                destination = "/lcopilot/combined-dashboard";
                console.log("✅ Retry: Routing to CombinedDashboard");
              } else if (retryCompanySize === "medium" || retryCompanySize === "large") {
                destination = "/lcopilot/enterprise-dashboard";
                console.log("✅ Retry: Routing to EnterpriseDashboard");
              }
            }
          }
        } catch (retryErr) {
          console.warn("Retry failed:", retryErr);
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