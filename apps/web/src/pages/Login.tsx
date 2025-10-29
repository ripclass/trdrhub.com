import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { FileText, Eye, EyeOff, Mail, Lock } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    // Mock authentication - replace with real API call
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      toast({
        title: "Login Successful",
        description: "Welcome back to LCopilot!",
      });
      
      // Redirect to dashboard
      window.location.href = "/dashboard";
    } catch (error) {
      toast({
        title: "Login Failed",
        description: "Please check your credentials and try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-secondary/20 to-primary/5 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Logo Header */}
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
          <p className="text-muted-foreground">
            Sign in to validate your LC documents
          </p>
        </div>

        {/* Login Form */}
        <Card className="shadow-strong border-0">
          <CardHeader className="space-y-2 text-center">
            <CardTitle className="text-xl">Welcome Back</CardTitle>
            <CardDescription>
              Enter your credentials to access your dashboard
            </CardDescription>
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
                    onClick={() => setShowPassword(!showPassword)}
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
                <Link
                  to="/forgot-password"
                  className="text-sm text-primary hover:underline"
                >
                  Forgot password?
                </Link>
              </div>

              <Button
                type="submit"
                className="w-full bg-gradient-primary hover:opacity-90"
                disabled={isLoading}
              >
                {isLoading ? "Signing in..." : "Sign In"}
              </Button>
            </form>

            <div className="mt-6">
              <Separator className="my-4" />
              <div className="text-center text-sm text-muted-foreground">
                Don't have an account?{" "}
                <Link
                  to="/register"
                  className="text-primary hover:underline font-medium"
                >
                  Create account
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Trust Indicators */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-success rounded-full"></div>
              500+ Exporters
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-success rounded-full"></div>
              99.2% Uptime
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-success rounded-full"></div>
              Bank Approved
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}