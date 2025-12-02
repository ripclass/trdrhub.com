/**
 * LCopilot Smart Router
 * 
 * Redirects users to the appropriate LCopilot dashboard based on their role AND company size.
 * This is the entry point when clicking "LCopilot" from the Hub.
 * 
 * Routing Logic:
 * - Banks → Bank Dashboard
 * - Enterprise/Large companies → Enterprise Dashboard
 * - Combined (both exporter+importer) SME → Combined Dashboard
 * - Importer SME → Importer Dashboard
 * - Exporter/Logistics SME → Exporter Dashboard
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getOnboardingStatus } from "@/api/onboarding";
import { Loader2, FileCheck } from "lucide-react";

export default function LcopilotRouter() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("Loading your dashboard...");

  useEffect(() => {
    const determineDestination = async () => {
      try {
        const onboardingStatus = await Promise.race([
          getOnboardingStatus(),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000))
        ]) as any;

        if (onboardingStatus) {
          const role = onboardingStatus.role;
          const details = onboardingStatus.details as Record<string, any> | undefined;
          const businessTypes = Array.isArray(details?.business_types) ? details.business_types : [];
          const companyType = details?.company?.type;
          const companySize = details?.company?.size;

          // Check if user is "both" exporter/importer
          const hasBoth = businessTypes.includes("exporter") && businessTypes.includes("importer");
          const isCompanyTypeBoth = companyType === "both" || 
                                    companyType === "Both Exporter & Importer" ||
                                    companyType === "both_exporter_importer";
          const isCombinedUser = hasBoth || isCompanyTypeBoth;

          // Check if large company (established = large, enterprise = enterprise)
          const isLargeCompany = companySize === "large" || 
                                 companySize === "enterprise" || 
                                 companySize === "established";

          // Determine destination based on role AND size
          let destination = "/lcopilot/exporter-dashboard";

          // 1. Bank users always go to bank dashboard
          if (role === "bank_officer" || role === "bank_admin") {
            destination = "/lcopilot/bank-dashboard";
            setStatus("Redirecting to Bank Dashboard...");
          }
          // 2. Tenant admins (large companies) go to enterprise dashboard
          else if (role === "tenant_admin") {
            destination = "/lcopilot/enterprise-dashboard";
            setStatus("Redirecting to Enterprise Dashboard...");
          }
          // 3. Large companies (by size) go to enterprise dashboard
          else if (isLargeCompany) {
            destination = "/lcopilot/enterprise-dashboard";
            setStatus("Redirecting to Enterprise Dashboard...");
          }
          // 4. Combined users (SME) go to combined dashboard
          else if (isCombinedUser) {
            destination = "/lcopilot/combined-dashboard";
            setStatus("Redirecting to Combined Dashboard...");
          }
          // 5. Importers go to importer dashboard
          else if (role === "importer" || companyType === "importer") {
            destination = "/lcopilot/importer-dashboard";
            setStatus("Redirecting to Importer Dashboard...");
          }
          // 6. Default to exporter dashboard (exporters, logistics, etc.)
          else {
            setStatus("Redirecting to Exporter Dashboard...");
          }

          // Small delay for visual feedback
          setTimeout(() => {
            navigate(destination, { replace: true });
          }, 300);
        } else {
          // No status, default to exporter
          navigate("/lcopilot/exporter-dashboard", { replace: true });
        }
      } catch (error) {
        console.warn("Failed to determine user role, defaulting to exporter:", error);
        navigate("/lcopilot/exporter-dashboard", { replace: true });
      }
    };

    determineDestination();
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-500/10 mb-6">
          <FileCheck className="w-8 h-8 text-blue-400" />
        </div>
        <div className="flex items-center justify-center gap-3 mb-4">
          <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
          <span className="text-lg text-white">{status}</span>
        </div>
        <p className="text-sm text-slate-400">Please wait...</p>
      </div>
    </div>
  );
}
