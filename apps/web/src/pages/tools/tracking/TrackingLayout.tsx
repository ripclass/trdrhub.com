/**
 * TrackingLayout - Dashboard layout for Container Tracker
 * Uses DashboardLayout pattern for consistency with LCopilot
 */
import { Outlet } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { TrackingSidebar } from "@/components/tools/TrackingSidebar";

export default function TrackingLayout() {
  return (
    <DashboardLayout
      sidebar={<TrackingSidebar />}
      breadcrumbs={[
        { label: "Hub", href: "/hub" },
        { label: "Container Tracker" },
      ]}
      title="Container Tracker"
    >
      <Outlet />
    </DashboardLayout>
  );
}
