/**
 * SanctionsLayout - Dashboard layout for Sanctions Screener
 * Uses DashboardLayout pattern for consistency with LCopilot
 */
import { Outlet } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { SanctionsSidebar } from "@/components/tools/SanctionsSidebar";

export default function SanctionsLayout() {
  return (
    <DashboardLayout
      sidebar={<SanctionsSidebar />}
      breadcrumbs={[
        { label: "Hub", href: "/hub" },
        { label: "Sanctions Screener" },
      ]}
      title="Sanctions Screener"
    >
      <Outlet />
    </DashboardLayout>
  );
}
