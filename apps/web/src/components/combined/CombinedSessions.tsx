import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { useCombined, type ViewMode } from "@/hooks/use-combined";
import { CheckCircle, Truck, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useMemo } from "react";

export interface Session {
  id: string;
  type: "export" | "import";
  counterparty: string;
  amount: string;
  status: string;
  updatedAt: string;
  lcNumber?: string;
}

interface CombinedSessionsProps {
  exportSessions?: Session[];
  importSessions?: Session[];
  isLoading?: boolean;
  onSessionClick?: (session: Session) => void;
}

export function CombinedSessions({
  exportSessions = [],
  importSessions = [],
  isLoading = false,
  onSessionClick,
}: CombinedSessionsProps) {
  const { viewMode, filters } = useCombined();

  // Filter sessions based on viewMode and filters
  const filteredExportSessions = useMemo(() => {
    if (viewMode === "import") return [];
    
    let filtered = [...exportSessions];
    
    // Apply status filter
    if (filters.status && filters.status.length > 0) {
      filtered = filtered.filter(s => filters.status?.includes(s.status.toLowerCase()));
    }
    
    // Apply bank filter
    if (filters.bank && filters.bank.length > 0) {
      filtered = filtered.filter(s => filters.bank?.some(b => s.counterparty.toLowerCase().includes(b.toLowerCase())));
    }
    
    return filtered;
  }, [exportSessions, viewMode, filters]);

  const filteredImportSessions = useMemo(() => {
    if (viewMode === "export") return [];
    
    let filtered = [...importSessions];
    
    // Apply status filter
    if (filters.status && filters.status.length > 0) {
      filtered = filtered.filter(s => filters.status?.includes(s.status.toLowerCase()));
    }
    
    // Apply bank filter
    if (filters.bank && filters.bank.length > 0) {
      filtered = filtered.filter(s => filters.bank?.some(b => s.counterparty.toLowerCase().includes(b.toLowerCase())));
    }
    
    return filtered;
  }, [importSessions, viewMode, filters]);

  const renderSessionCard = (session: Session) => {
    const isExport = session.type === "export";
    const dashboardUrl = isExport 
      ? `/lcopilot/exporter-dashboard?session=${session.id}`
      : `/lcopilot/importer-dashboard?session=${session.id}`;

    return (
      <Card
        key={session.id}
        className="border-border/40 shadow-sm transition-colors hover:border-primary/30 cursor-pointer"
        onClick={() => onSessionClick?.(session)}
      >
        <CardHeader className="space-y-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-foreground">
              {session.lcNumber || session.id}
            </CardTitle>
            <Badge variant="outline" className={`text-xs ${isExport ? 'text-primary' : 'text-info'}`}>
              {isExport ? 'Export' : 'Import'}
            </Badge>
          </div>
          <CardDescription className="text-sm text-muted-foreground">
            {session.counterparty} • {session.amount}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p className="flex items-center gap-2 text-foreground">
            {isExport ? (
              <CheckCircle className="h-4 w-4 text-success" />
            ) : (
              <Truck className="h-4 w-4 text-info" />
            )}{" "}
            {session.status}
          </p>
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Updated {session.updatedAt}</span>
            <Button
              asChild
              variant="ghost"
              size="sm"
              className="h-8 px-2 text-primary"
              onClick={(e) => e.stopPropagation()}
            >
              <Link to={dashboardUrl}>Open workspace</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border/40 bg-card/50 shadow-strong backdrop-blur p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Skeleton className="h-6 w-48 mb-2" />
              <Skeleton className="h-4 w-64" />
            </div>
            <Skeleton className="h-10 w-48" />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {[1, 2].map((i) => (
              <Card key={i} className="border-border/40">
                <CardHeader>
                  <Skeleton className="h-5 w-32 mb-2" />
                  <Skeleton className="h-4 w-48" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-4 w-full mb-2" />
                  <Skeleton className="h-4 w-24" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const hasExportSessions = filteredExportSessions.length > 0;
  const hasImportSessions = filteredImportSessions.length > 0;
  const hasAnySessions = hasExportSessions || hasImportSessions;

  if (!hasAnySessions && viewMode !== "all") {
    return (
      <div className="rounded-2xl border border-border/40 bg-card/50 shadow-strong backdrop-blur p-6">
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">
            No {viewMode === "export" ? "export" : "import"} sessions found.
          </p>
          <Button asChild variant="outline">
            <Link to={`/lcopilot/${viewMode === "export" ? "exporter" : "importer"}-dashboard?section=upload`}>
              Upload {viewMode === "export" ? "Export" : "Import"} LC
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  if (!hasAnySessions) {
    return (
      <div className="rounded-2xl border border-border/40 bg-card/50 shadow-strong backdrop-blur p-6">
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">No validation sessions found.</p>
          <div className="flex gap-4 justify-center">
            <Button asChild variant="outline">
              <Link to="/lcopilot/exporter-dashboard?section=upload">Upload Export LC</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/lcopilot/importer-dashboard?section=upload">Upload Import LC</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // If viewMode is "all", show tabs
  if (viewMode === "all") {
    return (
      <div className="rounded-2xl border border-border/40 bg-card/50 shadow-strong backdrop-blur">
        <Tabs defaultValue={hasExportSessions ? "exports" : "imports"} className="w-full">
          <div className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-foreground">Validation Sessions</h2>
              <p className="text-sm text-muted-foreground">
                Export and import LC progress in one place. Filter by tab to focus faster.
              </p>
            </div>
            <TabsList className="grid w-full grid-cols-2 md:w-auto">
              <TabsTrigger value="exports">
                Export LCs {hasExportSessions && `(${filteredExportSessions.length})`}
              </TabsTrigger>
              <TabsTrigger value="imports">
                Import LCs {hasImportSessions && `(${filteredImportSessions.length})`}
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="exports" className="p-6 pt-0">
            {hasExportSessions ? (
              <div className="grid gap-4 md:grid-cols-2">
                {filteredExportSessions.map(renderSessionCard)}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-muted-foreground mb-4">No export sessions found.</p>
                <Button asChild variant="outline">
                  <Link to="/lcopilot/exporter-dashboard?section=upload">Upload Export LC</Link>
                </Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="imports" className="p-6 pt-0">
            {hasImportSessions ? (
              <div className="grid gap-4 md:grid-cols-2">
                {filteredImportSessions.map(renderSessionCard)}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-muted-foreground mb-4">No import sessions found.</p>
                <Button asChild variant="outline">
                  <Link to="/lcopilot/importer-dashboard?section=upload">Upload Import LC</Link>
                </Button>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    );
  }

  // Single mode view (export or import only)
  const sessions = viewMode === "export" ? filteredExportSessions : filteredImportSessions;
  const typeLabel = viewMode === "export" ? "Export" : "Import";

  return (
    <div className="rounded-2xl border border-border/40 bg-card/50 shadow-strong backdrop-blur p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-foreground">{typeLabel} Validation Sessions</h2>
        <p className="text-sm text-muted-foreground">
          Track your {typeLabel.toLowerCase()} LC progress and resolve discrepancies.
        </p>
      </div>
      {sessions.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {sessions.map(renderSessionCard)}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">No {typeLabel.toLowerCase()} sessions found.</p>
          <Button asChild variant="outline">
            <Link to={`/lcopilot/${viewMode === "export" ? "exporter" : "importer"}-dashboard?section=upload`}>
              Upload {typeLabel} LC
            </Link>
          </Button>
        </div>
      )}
    </div>
  );
}

