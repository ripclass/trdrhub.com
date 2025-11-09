import * as React from "react";
import { useAuth } from "@/hooks/use-auth";
import { getAdminService } from "@/lib/admin/services";
import { MFAVerificationDialog } from "./MFAVerification";
import type { AdminSettings } from "@/lib/admin/types";

/**
 * MFA Enforcement Hook
 * Checks if MFA is required based on admin settings and user role,
 * and enforces MFA verification before allowing access to the app.
 */
export function useMFAEnforcement() {
  const { user } = useAuth();
  const [needsMFA, setNeedsMFA] = React.useState(false);
  const [isMFAVerified, setIsMFAVerified] = React.useState(false);
  const [settings, setSettings] = React.useState<AdminSettings | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  // Fetch admin settings
  React.useEffect(() => {
    const loadSettings = async () => {
      try {
        const adminService = getAdminService();
        const adminSettings = await adminService.getSettings();
        setSettings(adminSettings);
      } catch (error) {
        console.warn("Failed to load admin settings for MFA check", error);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadSettings();
  }, []);

  // Check if MFA is required
  React.useEffect(() => {
    if (!user || isLoading || !settings) {
      setNeedsMFA(false);
      return;
    }

    // Check if MFA is enforced globally
    const mfaEnforced = settings.authentication.mfaEnforced;
    
    // Check if user role requires MFA
    const rolesRequiringMFA = ["admin", "bank"];
    const roleRequiresMFA = rolesRequiringMFA.includes(user.role);

    // Check if user has MFA enabled (in a real app, check user.mfaEnabled)
    // For now, we'll check if MFA is enforced OR role requires it
    const requiresMFA = mfaEnforced || roleRequiresMFA;

    setNeedsMFA(requiresMFA);
    
    // If MFA is not required, mark as verified
    if (!requiresMFA) {
      setIsMFAVerified(true);
    }
  }, [user, settings, isLoading]);

  const handleMFAVerified = React.useCallback(() => {
    setIsMFAVerified(true);
    // Store MFA verification in session storage (in a real app, use secure token)
    sessionStorage.setItem("mfa_verified", "true");
  }, []);

  // Check session storage for previous MFA verification
  React.useEffect(() => {
    if (needsMFA && sessionStorage.getItem("mfa_verified") === "true") {
      setIsMFAVerified(true);
    }
  }, [needsMFA]);

  return {
    needsMFA,
    isMFAVerified,
    isLoading,
    handleMFAVerified,
  };
}

/**
 * MFA Enforcement Component
 * Shows MFA dialog when required and blocks access until verified.
 */
export function MFAEnforcement() {
  const { needsMFA, isMFAVerified, isLoading, handleMFAVerified } = useMFAEnforcement();

  // Don't render anything if loading or MFA not needed
  if (isLoading || !needsMFA) {
    return null;
  }

  // Block access until MFA is verified
  if (!isMFAVerified) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
        <MFAVerificationDialog
          required={true}
          onVerified={handleMFAVerified}
        />
      </div>
    );
  }

  return null;
}

