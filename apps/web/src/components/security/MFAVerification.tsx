import * as React from "react";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Shield, RefreshCw, AlertCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface MFAProps {
  required?: boolean;
  onVerified?: () => void;
  onCancel?: () => void;
}

export function MFAVerificationDialog({ required = false, onVerified, onCancel }: MFAProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [code, setCode] = React.useState("");
  const [isVerifying, setIsVerifying] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = React.useState(0);

  // Check if user needs MFA
  const needsMFA = React.useMemo(() => {
    // In a real app, check user.mfaEnabled or user.role requires MFA
    if (!user) return false;
    const rolesRequiringMFA = ["admin", "bank"];
    return required || rolesRequiringMFA.includes(user.role);
  }, [user, required]);

  React.useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const handleVerify = async () => {
    if (code.length !== 6) {
      setError("Please enter a 6-digit code");
      return;
    }

    setIsVerifying(true);
    setError(null);

    try {
      // In a real app, call API: await api.post('/auth/verify-mfa', { code })
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Mock verification - in real app, check response
      if (code === "123456") {
        toast({
          title: "MFA Verified",
          description: "Your identity has been verified.",
        });
        onVerified?.();
      } else {
        setError("Invalid verification code. Please try again.");
      }
    } catch (err) {
      setError("Verification failed. Please try again.");
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResendCode = async () => {
    if (resendCooldown > 0) return;

    try {
      // In a real app, call API: await api.post('/auth/resend-mfa')
      setResendCooldown(60);
      toast({
        title: "Code Sent",
        description: "A new verification code has been sent to your device.",
      });
    } catch (err) {
      toast({
        title: "Failed to Resend",
        description: "Could not send verification code. Please try again.",
        variant: "destructive",
      });
    }
  };

  if (!needsMFA) return null;

  return (
    <Dialog open={true} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <DialogTitle>Two-Factor Authentication</DialogTitle>
          </div>
          <DialogDescription>
            Enter the 6-digit code from your authenticator app to continue.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Verification Code</Label>
            <Input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={code}
              onChange={(e) => {
                const value = e.target.value.replace(/\D/g, "").slice(0, 6);
                setCode(value);
                setError(null);
              }}
              placeholder="000000"
              className="text-center text-2xl tracking-widest font-mono"
              autoFocus
            />
            {error && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span>{error}</span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between text-sm">
            <Button
              variant="link"
              size="sm"
              onClick={handleResendCode}
              disabled={resendCooldown > 0}
              className="h-auto p-0"
            >
              {resendCooldown > 0 ? (
                `Resend code in ${resendCooldown}s`
              ) : (
                <>
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Resend Code
                </>
              )}
            </Button>
            {onCancel && (
              <Button variant="link" size="sm" onClick={onCancel} className="h-auto p-0">
                Cancel
              </Button>
            )}
          </div>

          <div className="flex items-center justify-end gap-2">
            <Button onClick={handleVerify} disabled={isVerifying || code.length !== 6}>
              {isVerifying ? "Verifying..." : "Verify"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function MFARequiredBanner() {
  const { user } = useAuth();
  const [showSetup, setShowSetup] = React.useState(false);

  const needsMFA = React.useMemo(() => {
    if (!user) return false;
    const rolesRequiringMFA = ["admin", "bank"];
    return rolesRequiringMFA.includes(user.role);
  }, [user]);

  if (!needsMFA) return null;

  return (
    <Card className="border-warning bg-warning/5">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-warning" />
            <CardTitle className="text-sm">Two-Factor Authentication Required</CardTitle>
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowSetup(true)}>
            Setup MFA
          </Button>
        </div>
        <CardDescription className="text-xs">
          Your role requires two-factor authentication. Please set it up to continue using the platform.
        </CardDescription>
      </CardHeader>
    </Card>
  );
}

