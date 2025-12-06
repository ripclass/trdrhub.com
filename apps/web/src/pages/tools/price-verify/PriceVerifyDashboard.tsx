/**
 * PriceVerifyDashboard - Dashboard layout for Price Verify
 * Uses DashboardLayout pattern for consistency with LCopilot
 */
import { Outlet } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PriceVerifySidebar } from "@/components/tools/PriceVerifySidebar";

export default function PriceVerifyDashboard() {
  return (
    <DashboardLayout
      sidebar={<PriceVerifySidebar />}
      breadcrumbs={[
        { label: "Hub", href: "/hub" },
        { label: "Price Verify" },
      ]}
      title="Price Verify"
    >
      <Outlet />
    </DashboardLayout>
  );
}
