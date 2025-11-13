import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCombined, type ViewMode } from "@/hooks/use-combined";
import { FileText, ShieldCheck, AlertTriangle, Navigation } from "lucide-react";
import { useMemo } from "react";

export interface KPIData {
  activeLCs: {
    total: number;
    export: number;
    import: number;
  };
  approvalRate: {
    total: number;
    export: number;
    import: number;
  };
  pendingActions: {
    total: number;
    export: number;
    import: number;
  };
  avgTurnaround: {
    total: string;
    export: string;
    import: string;
  };
}

interface CombinedKPIsProps {
  data?: KPIData;
  isLoading?: boolean;
  onKpiClick?: (kpi: string, mode?: ViewMode) => void;
}

export function CombinedKPIs({ data, isLoading = false, onKpiClick }: CombinedKPIsProps) {
  const { viewMode } = useCombined();

  // Filter data based on viewMode
  const filteredData = useMemo(() => {
    if (!data) return null;

    if (viewMode === "export") {
      return {
        activeLCs: { total: data.activeLCs.export, export: data.activeLCs.export, import: 0 },
        approvalRate: { total: data.approvalRate.export, export: data.approvalRate.export, import: 0 },
        pendingActions: { total: data.pendingActions.export, export: data.pendingActions.export, import: 0 },
        avgTurnaround: { total: data.avgTurnaround.export, export: data.avgTurnaround.export, import: "" },
      };
    } else if (viewMode === "import") {
      return {
        activeLCs: { total: data.activeLCs.import, export: 0, import: data.activeLCs.import },
        approvalRate: { total: data.approvalRate.import, export: 0, import: data.approvalRate.import },
        pendingActions: { total: data.pendingActions.import, export: 0, import: data.pendingActions.import },
        avgTurnaround: { total: data.avgTurnaround.import, export: "", import: data.avgTurnaround.import },
      };
    }

    return data; // "all" mode
  }, [data, viewMode]);

  const stats = [
    {
      label: 'Active LCs',
      value: filteredData?.activeLCs.total ?? 0,
      helper: viewMode === "all" 
        ? `Export ${filteredData?.activeLCs.export ?? 0} • Import ${filteredData?.activeLCs.import ?? 0}`
        : viewMode === "export" 
        ? `${filteredData?.activeLCs.export ?? 0} active`
        : `${filteredData?.activeLCs.import ?? 0} active`,
      icon: <FileText className="h-5 w-5 text-primary" />,
      key: 'activeLCs',
    },
    {
      label: 'Approval Rate',
      value: `${filteredData?.approvalRate.total ?? 0}%`,
      helper: 'Last 30 days',
      icon: <ShieldCheck className="h-5 w-5 text-success" />,
      key: 'approvalRate',
    },
    {
      label: 'Pending Actions',
      value: filteredData?.pendingActions.total ?? 0,
      helper: 'Needs review today',
      icon: <AlertTriangle className="h-5 w-5 text-amber-500" />,
      key: 'pendingActions',
    },
    {
      label: 'Average Turnaround',
      value: filteredData?.avgTurnaround.total ?? '0 days',
      helper: 'Across all banks',
      icon: <Navigation className="h-5 w-5 text-info" />,
      key: 'avgTurnaround',
    },
  ];

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.key} className="border-border/40 shadow-soft">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-5 w-5 rounded" />
            </CardHeader>
            <CardContent className="space-y-1">
              <Skeleton className="h-8 w-16" />
              <Skeleton className="h-3 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {stats.map((stat) => (
        <Card
          key={stat.key}
          className="border-border/40 shadow-soft cursor-pointer transition-all hover:shadow-md hover:border-primary/30"
          onClick={() => onKpiClick?.(stat.key, viewMode)}
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardDescription className="text-xs uppercase tracking-wide text-muted-foreground">
              {stat.label}
            </CardDescription>
            {stat.icon}
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-2xl font-semibold text-foreground">{stat.value}</div>
            <p className="text-xs text-muted-foreground">{stat.helper}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

