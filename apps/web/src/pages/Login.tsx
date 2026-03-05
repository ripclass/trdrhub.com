import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { 
  Eye, 
  EyeOff, 
  Mail, 
  Lock, 
  ArrowRight,
  FileCheck,
  DollarSign,
  Ship,
  Shield,
  BarChart3,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { getOnboardingStatus } from "@/api/onboarding";

const FEATURES = [
  { icon: FileCheck, label: "LC Validation" },
  { icon: DollarSign, label: "Price Verification" },
  { icon: Ship, label: "Shipment Tracking" },
  { icon: Shield, label: "Sanctions Screening" },
  { icon: BarChart3, label: "Trade Analytics" },
];

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { loginWithEmail } = useAuth();

  // Get returnUrl from query params (e.g., /login?returnUrl=/tracking/dashboard)
  const returnUrl = searchParams.get("returnUrl");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const profile = await loginWithEmail(email, password);
      toast({
        title: "Welcome back!",
        description: "Successfully signed in to TRDR Hub.",
      });

      // If returnUrl is provided, use it (for redirects from protected pages)
      if (returnUrl) {
        setIsLoading(false);
        // Use window.location for a hard redirect to ensure it works
        // after auth state changes (React navigate can get lost in re-renders)
        window.location.href = returnUrl;
        return;
      }

      // Default routing: Most users go to Hub, only banks go to bank dashboard
      let destination = "/hub";
      
      try {
        const status = await Promise.race([
          getOnboardingStatus(),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000))
        ]) as any;
        
        if (status) {
          const backendRole = status.role;
          
          // Only bank users go to bank dashboard, everyone else goes to Hub
          if (backendRole === "bank_officer" || backendRole === "bank_admin") {
            destination = "/lcopilot/bank-dashboard";
          }
        }
      } catch (err) {
        console.warn("Onboarding status check failed, defaulting to Hub:", err);
        // Default to Hub for all users if status check fails
        // profile.role is already mapped to "bank" for bank_officer/bank_admin
        if (profile.role === "bank") {
          destination = "/lcopilot/bank-dashboard";
        }
      }
      
      setIsLoading(false);
      navigate(destination);
    } catch (error: any) {
      const message = error?.message || "Please check your credentials and try again.";
      toast({
        title: "Login failed",
        description: message,
        variant: "destructive",
      });
      setIsLoading(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2 bg-[#00261C]">
      {/* Left Column - Login Form */}
      <div className="relative flex flex-col p-6 md:p-10 justify-center">
        {/* Background effects */}
        <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-[#B2F273]/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-[#B2F273]/5 rounded-full blur-3xl" />
        
        {/* Header with logo */}
        <div className="absolute top-6 left-6 md:top-10 md:left-10 z-10">
          <Link to="/" className="flex items-center gap-2">
            <img 
              src="/logo-dark-v2.png" 
              alt="TRDR Hub" 
              className="h-8 w-auto object-contain"
            />
          </Link>
        </div>
        
        {/* Form container */}
        <div className="w-full max-w-sm mx-auto relative z-10">
          {/* Form header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-2 font-display">Welcome back</h1>
            <p className="text-[#EDF5F2]/60">
              Sign in to access your trade dashboard
            </p>
          </div>

          {/* Login form */}
          <form onSubmit={handleLogin} className="space-y-5">
            {/* Email field */}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium text-[#EDF5F2]/80">
                Email
              </Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#EDF5F2]/40" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 h-11 bg-[#00382E]/50 border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/30 focus:border-[#B2F273]/50 focus:ring-[#B2F273]/20 rounded-xl"
                  required
                />
              </div>
            </div>

            {/* Password field */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-sm font-medium text-[#EDF5F2]/80">
                  Password
                </Label>
                <Link 
                  to="/forgot-password" 
                  className="text-sm text-[#B2F273] hover:text-[#a3e662]"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#EDF5F2]/40" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
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

            {/* Submit button */}
            <Button 
              type="submit" 
              disabled={isLoading}
              className="w-full h-11 bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-bold rounded-xl"
            >
              {isLoading ? "Signing in..." : "Sign In"}
              {!isLoading && <ArrowRight className="w-4 h-4 ml-2" />}
            </Button>
          </form>

          {/* Separator */}
          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[#EDF5F2]/10" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-[#00261C] px-2 text-[#EDF5F2]/40">Or continue with</span>
            </div>
          </div>

          {/* Google OAuth placeholder */}
          <Button 
            variant="outline" 
            className="w-full h-11 border-[#EDF5F2]/10 text-[#EDF5F2]/80 hover:bg-[#00382E] hover:text-white bg-transparent rounded-xl"
            disabled
          >
            <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Google
            <span className="ml-2 text-xs text-[#EDF5F2]/40">(Coming soon)</span>
          </Button>

          {/* Sign up link */}
          <p className="mt-8 text-center text-sm text-[#EDF5F2]/60">
            Don't have an account?{" "}
            <Link to="/register" className="text-[#B2F273] hover:text-[#a3e662] font-medium">
              Create free account
            </Link>
          </p>
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
            backgroundImage: `url('https://images.unsplash.com/photo-1578575437130-527eed3abbec?q=80&w=2070&auto=format&fit=crop')`,
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
            15 AI-powered tools to validate documents, verify prices, screen sanctions, and track shipments — all in one place.
          </p>

          {/* Features grid */}
          <div className="grid grid-cols-2 gap-4 mb-12">
            {FEATURES.map((feature) => {
              const Icon = feature.icon;
              return (
                <div 
                  key={feature.label}
                  className="flex items-center gap-3 p-4 rounded-xl bg-[#00382E]/50 border border-[#EDF5F2]/10 backdrop-blur-sm"
                >
                  <div className="w-10 h-10 rounded-lg bg-[#B2F273]/10 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5 text-[#B2F273]" />
                  </div>
                  <span className="text-sm font-medium text-[#EDF5F2]/80">{feature.label}</span>
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
