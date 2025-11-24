import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import type { ResultsTab } from "./dashboardTabs";
import ExporterSidebar from "./ExporterSidebar";
import DashboardNav from "./DashboardNav";

type LayoutProps = {
  children: React.ReactNode;
  activeTab: ResultsTab;
  onTabChange: (tab: ResultsTab) => void;
};

export default function ExporterDashboardLayout({ children, activeTab, onTabChange }: LayoutProps) {
  return (
    <DashboardLayout
      sidebar={<ExporterSidebar activeTab={activeTab} onTabChange={onTabChange} />}
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Exporter Dashboard" },
      ]}
      title="Exporter LC Workspace"
      topbar={<DashboardNav activeTab={activeTab} onTabChange={onTabChange} />}
      actions={
        <Button asChild size="sm">
          <Link to="/lcopilot/upload-lc">Upload LC Package</Link>
        </Button>
      }
    >
      <div className="pb-10">{children}</div>
    </DashboardLayout>
  );
}

