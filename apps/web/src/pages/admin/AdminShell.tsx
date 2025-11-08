// AdminShell - section-based admin dashboard with DashboardLayout
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { useAdminAuth } from "@/lib/admin/auth";
import { useToast } from "@/hooks/use-toast";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";
import { useOnboarding } from "@/hooks/use-onboarding";

// Import section components (will create these next)
import { AdminOverview } from "./sections/AdminOverview";
import { OpsMonitoring } from "./sections/ops/Monitoring";
import { OpsJobs } from "./sections/ops/Jobs";
import { OpsAlerts } from "./sections/ops/Alerts";
import { AuditLogs } from "./sections/audit/Logs";
import { AuditApprovals } from "./sections/audit/Approvals";
import { AuditCompliance } from "./sections/audit/Compliance";
import { SecurityUsers } from "./sections/security/Users";
import { SecurityAccess } from "./sections/security/Access";
import { SecuritySessions } from "./sections/security/Sessions";
import { BillingOverview } from "./sections/billing/Overview";
import { BillingInvoicesPayments } from "./sections/billing/InvoicesPayments";
import { BillingRecognition } from "./sections/billing/Recognition";
import { BillingTaxes } from "./sections/billing/Taxes";
import { BillingPlans } from "./sections/billing/Plans";
import { BillingAdjustments } from "./sections/billing/Adjustments";
import { BillingDisputes } from "./sections/billing/Disputes";
import { PartnersRegistry } from "./sections/partners/Registry";
import { PartnersConnectors } from "./sections/partners/Connectors";
import { PartnersWebhooks } from "./sections/partners/Webhooks";
import { LLMPrompts } from "./sections/llm/Prompts";
import { LLMBudgets } from "./sections/llm/Budgets";
import { LLMEvaluations } from "./sections/llm/Evaluations";
import { ComplianceResidency } from "./sections/compliance/Residency";
import { ComplianceRetention } from "./sections/compliance/Retention";
import { ComplianceLegalHolds } from "./sections/compliance/LegalHolds";
import { SystemFeatureFlags } from "./sections/system/FeatureFlags";
import { SystemReleases } from "./sections/system/Releases";
import { SystemSettings } from "./sections/system/Settings";

// Define all possible sections
const SECTION_OPTIONS = [
  "overview",
  "ops-monitoring",
  "ops-jobs",
  "ops-alerts",
  "audit-logs",
  "audit-approvals",
  "audit-compliance",
  "security-users",
  "security-access",
  "security-sessions",
  "billing-overview",
  "billing-invoices-payments",
  "billing-recognition",
  "billing-taxes",
  "billing-plans",
  "billing-adjustments",
  "billing-disputes",
  "partners-registry",
  "partners-connectors",
  "partners-webhooks",
  "llm-prompts",
  "llm-budgets",
  "llm-evaluations",
  "compliance-residency",
  "compliance-retention",
  "compliance-legal-holds",
  "system-feature-flags",
  "system-releases",
  "system-settings",
] as const;

type Section = (typeof SECTION_OPTIONS)[number];

export default function AdminShell() {
  const { user, isAuthenticated } = useAdminAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const { needsOnboarding, isLoading: isLoadingOnboarding } = useOnboarding();

  const [showOnboarding, setShowOnboarding] = useState(false);
  const [activeSection, setActiveSection] = useState<Section>(
    (searchParams.get("section") as Section) || "overview"
  );

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/admin/login");
    }
  }, [isAuthenticated, navigate]);

  // Check onboarding status on mount
  useEffect(() => {
    if (isAuthenticated && !isLoadingOnboarding && needsOnboarding) {
      setShowOnboarding(true);
    }
  }, [isAuthenticated, needsOnboarding, isLoadingOnboarding]);

  // Sync activeSection with URL search params
  useEffect(() => {
    const current = (searchParams.get("section") as Section) || "overview";
    if (current !== activeSection) {
      setActiveSection(current);
    }
  }, [searchParams, activeSection]);

  const handleSectionChange = (section: Section) => {
    setActiveSection(section);

    const next = new URLSearchParams(searchParams);

    if (section === "overview") {
      next.delete("section");
    } else {
      next.set("section", section);
    }

    setSearchParams(next, { replace: true });
  };

  if (!isAuthenticated) {
    return <div>Loading...</div>;
  }

  return (
    <>
      <DashboardLayout
        sidebar={<AdminSidebar activeSection={activeSection} onSectionChange={handleSectionChange} />}
        breadcrumbs={[
          { label: "Admin Console", href: "/admin" },
          ...(activeSection !== "overview"
            ? [{ label: activeSection.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ") }]
            : []),
        ]}
      >
        <div className="flex flex-1 flex-col gap-6 p-6 lg:p-8">
          {activeSection === "overview" && <AdminOverview />}
          {activeSection === "ops-monitoring" && <OpsMonitoring />}
          {activeSection === "ops-jobs" && <OpsJobs />}
          {activeSection === "ops-alerts" && <OpsAlerts />}
          {activeSection === "audit-logs" && <AuditLogs />}
          {activeSection === "audit-approvals" && <AuditApprovals />}
          {activeSection === "audit-compliance" && <AuditCompliance />}
          {activeSection === "security-users" && <SecurityUsers />}
          {activeSection === "security-access" && <SecurityAccess />}
          {activeSection === "security-sessions" && <SecuritySessions />}
          {activeSection === "billing-overview" && <BillingOverview />}
          {activeSection === "billing-invoices-payments" && <BillingInvoicesPayments />}
          {activeSection === "billing-recognition" && <BillingRecognition />}
          {activeSection === "billing-taxes" && <BillingTaxes />}
          {activeSection === "billing-plans" && <BillingPlans />}
          {activeSection === "billing-adjustments" && <BillingAdjustments />}
          {activeSection === "billing-disputes" && <BillingDisputes />}
          {activeSection === "partners-registry" && <PartnersRegistry />}
          {activeSection === "partners-connectors" && <PartnersConnectors />}
          {activeSection === "partners-webhooks" && <PartnersWebhooks />}
          {activeSection === "llm-prompts" && <LLMPrompts />}
          {activeSection === "llm-budgets" && <LLMBudgets />}
          {activeSection === "llm-evaluations" && <LLMEvaluations />}
          {activeSection === "compliance-residency" && <ComplianceResidency />}
          {activeSection === "compliance-retention" && <ComplianceRetention />}
          {activeSection === "compliance-legal-holds" && <ComplianceLegalHolds />}
          {activeSection === "system-feature-flags" && <SystemFeatureFlags />}
          {activeSection === "system-releases" && <SystemReleases />}
          {activeSection === "system-settings" && <SystemSettings />}
        </div>
      </DashboardLayout>

      {/* Onboarding Wizard */}
      <OnboardingWizard
        open={showOnboarding}
        onClose={() => setShowOnboarding(false)}
        onComplete={async () => {
          setShowOnboarding(false);
          toast({
            title: "Onboarding Complete",
            description: "Welcome to the Admin Console!",
          });
        }}
      />
    </>
  );
}

