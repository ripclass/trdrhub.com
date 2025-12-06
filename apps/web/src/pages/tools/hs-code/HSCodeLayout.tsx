/**
 * HSCodeLayout - Dashboard layout for HS Code Finder
 * Uses DashboardLayout pattern for consistency with LCopilot
 */
import { Outlet } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { HSCodeSidebar } from "@/components/tools/HSCodeSidebar";

export default function HSCodeLayout() {
  return (
    <DashboardLayout
      sidebar={<HSCodeSidebar />}
      breadcrumbs={[
        { label: "Hub", href: "/hub" },
        { label: "HS Code Finder" },
      ]}
      title="HS Code Finder"
    >
      <Outlet />
    </DashboardLayout>
  );
}
