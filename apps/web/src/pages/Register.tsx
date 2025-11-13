import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { FileText, ShieldCheck, Timer, Sparkles, ArrowRight, CheckCircle } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

export default function Register() {
  const { loginWithAuth0 } = useAuth();

  const handleAuth0Signup = async () => {
    try {
      // Auth0 signup/login uses the same OAuth flow
      // Auth0 will show signup option if user doesn't exist
      await loginWithAuth0();
    } catch (error) {
      console.error('Auth0 signup error:', error);
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
                Sign up with Auth0 to get started. After authentication, we'll guide you through a quick onboarding process to set up your workspace.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="rounded-xl bg-muted/50 p-6 space-y-4">
                <h4 className="font-medium text-foreground">What happens next?</h4>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                    <span>You'll be redirected to Auth0 to create your account</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                    <span>After signup, you'll complete a quick onboarding wizard</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                    <span>We'll collect your company type, size, and business details</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                    <span>Your workspace will be tailored based on your role and needs</span>
                  </li>
                </ul>
              </div>

              <Button
                onClick={handleAuth0Signup}
                className="w-full bg-gradient-primary hover:opacity-90 h-12 text-base font-semibold"
                size="lg"
              >
                Sign up with Auth0
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>

              <div className="text-center text-sm text-muted-foreground">
                Already have an account?{" "}
                <Link to="/login" className="font-medium text-primary hover:underline">
                  Sign in
                </Link>
              </div>

              <Separator />

              <div className="rounded-lg border border-border/40 bg-muted/30 p-4 text-xs text-muted-foreground">
                <p className="font-medium text-foreground mb-1">Secure authentication</p>
                <p>
                  We use Auth0 for enterprise-grade authentication. Your credentials are managed securely, and you can use single sign-on (SSO) if your organization supports it.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}