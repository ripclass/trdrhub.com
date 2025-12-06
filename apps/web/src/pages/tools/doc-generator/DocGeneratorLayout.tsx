/**
 * DocGeneratorLayout - Dashboard layout for Doc Generator
 * Uses DashboardLayout pattern for consistency with LCopilot
 */
import { Outlet } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { DocGeneratorSidebar } from "@/components/tools/DocGeneratorSidebar";

export default function DocGeneratorLayout() {
  return (
    <DashboardLayout
      sidebar={<DocGeneratorSidebar />}
      breadcrumbs={[
        { label: "Hub", href: "/hub" },
        { label: "Doc Generator" },
      ]}
      title="Doc Generator"
    >
      <Outlet />
    </DashboardLayout>
  );
}
