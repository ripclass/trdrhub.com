import * as React from "react";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";
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
import { AlertCircle, Clock, Shield } from "lucide-react";
import { Progress } from "@/components/ui/progress";

interface SessionTimeoutProps {
  timeoutMinutes?: number;
  warningMinutes?: number;
}

export function useSessionTimeout({ timeoutMinutes = 30, warningMinutes = 5 }: SessionTimeoutProps = {}) {
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [timeRemaining, setTimeRemaining] = React.useState<number | null>(null);
  const [showWarning, setShowWarning] = React.useState(false);
  const [showExpired, setShowExpired] = React.useState(false);
  const [lastActivity, setLastActivity] = React.useState(Date.now());

  // Reset activity timer on user interaction
  React.useEffect(() => {
    if (!user) return;

    const updateActivity = () => {
      setLastActivity(Date.now());
    };

    const events = ["mousedown", "keydown", "scroll", "touchstart"];
    events.forEach((event) => {
      window.addEventListener(event, updateActivity);
    });

    return () => {
      events.forEach((event) => {
        window.removeEventListener(event, updateActivity);
      });
    };
  }, [user]);

  // Monitor session timeout
  React.useEffect(() => {
    if (!user) {
      setTimeRemaining(null);
      setShowWarning(false);
      setShowExpired(false);
      return;
    }

    const timeoutMs = timeoutMinutes * 60 * 1000;
    const warningMs = warningMinutes * 60 * 1000;
    const checkInterval = 1000; // Check every second

    const interval = setInterval(() => {
      const elapsed = Date.now() - lastActivity;
      const remaining = timeoutMs - elapsed;
      const remainingSeconds = Math.max(0, Math.floor(remaining / 1000));
      const remainingMinutes = Math.floor(remainingSeconds / 60);

      setTimeRemaining(remainingSeconds);

      if (remaining <= 0) {
        // Session expired
        setShowExpired(true);
        setShowWarning(false);
        clearInterval(interval);
      } else if (remaining <= warningMs && !showWarning) {
        // Show warning
        setShowWarning(true);
        toast({
          title: "Session Expiring Soon",
          description: `Your session will expire in ${remainingMinutes} minute(s). Please save your work.`,
          variant: "default",
        });
      }
    }, checkInterval);

    return () => clearInterval(interval);
  }, [user, lastActivity, timeoutMinutes, warningMinutes, showWarning, toast]);

  const handleExtendSession = async () => {
    // In a real app, call API to refresh session
    setLastActivity(Date.now());
    setShowWarning(false);
    toast({
      title: "Session Extended",
      description: "Your session has been extended.",
    });
  };

  const handleLogout = async () => {
    await logout();
    setShowExpired(false);
    setShowWarning(false);
  };

  return {
    timeRemaining,
    showWarning,
    showExpired,
    handleExtendSession,
    handleLogout,
  };
}

export function SessionTimeoutDialog() {
  const { timeRemaining, showWarning, showExpired, handleExtendSession, handleLogout } = useSessionTimeout({
    timeoutMinutes: 30,
    warningMinutes: 5,
  });

  const remainingMinutes = timeRemaining ? Math.floor(timeRemaining / 60) : 0;
  const remainingSeconds = timeRemaining ? timeRemaining % 60 : 0;
  const progress = timeRemaining ? (timeRemaining / (30 * 60)) * 100 : 0;

  return (
    <>
      {/* Warning Dialog */}
      <Dialog open={showWarning} onOpenChange={() => {}}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-warning" />
              <DialogTitle>Session Expiring Soon</DialogTitle>
            </div>
            <DialogDescription>
              Your session will expire in {remainingMinutes}:{remainingSeconds.toString().padStart(2, "0")}. Please save your work.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Progress value={progress} className="h-2" />
            <div className="flex items-center justify-end gap-2">
              <Button variant="outline" onClick={handleLogout}>
                Logout
              </Button>
              <Button onClick={handleExtendSession}>Extend Session</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Expired Dialog */}
      <Dialog open={showExpired} onOpenChange={() => {}}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <DialogTitle>Session Expired</DialogTitle>
            </div>
            <DialogDescription>
              Your session has expired for security reasons. Please log in again to continue.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center justify-end">
            <Button onClick={handleLogout}>Go to Login</Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

