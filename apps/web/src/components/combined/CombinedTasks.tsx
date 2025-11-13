import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useCombined, type ViewMode } from "@/hooks/use-combined";
import { useMemo } from "react";
import { Link } from "react-router-dom";

export interface Task {
  id: string;
  type: "export" | "import";
  title: string;
  description: string;
  lcNumber: string;
  dueDate: string;
  priority: "high" | "medium" | "low";
  status: "pending" | "in_progress" | "completed";
}

interface CombinedTasksProps {
  exportTasks?: Task[];
  importTasks?: Task[];
  isLoading?: boolean;
  maxItems?: number;
}

export function CombinedTasks({
  exportTasks = [],
  importTasks = [],
  isLoading = false,
  maxItems = 5,
}: CombinedTasksProps) {
  const { viewMode } = useCombined();

  // Combine and filter tasks based on viewMode
  const allTasks = useMemo(() => {
    let combined: Task[] = [];
    
    if (viewMode === "all" || viewMode === "export") {
      combined = [...combined, ...exportTasks];
    }
    
    if (viewMode === "all" || viewMode === "import") {
      combined = [...combined, ...importTasks];
    }
    
    // Sort by priority and due date
    combined.sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 };
      const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
      if (priorityDiff !== 0) return priorityDiff;
      
      // Then by due date (sooner first)
      return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime();
    });
    
    return combined.slice(0, maxItems);
  }, [exportTasks, importTasks, viewMode, maxItems]);

  if (isLoading) {
    return (
      <Card className="md:col-span-2 border-border/40 shadow-sm">
        <CardHeader>
          <Skeleton className="h-6 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-start justify-between rounded-lg border border-border/40 bg-muted/40 p-4">
              <div className="flex-1">
                <Skeleton className="h-5 w-48 mb-2" />
                <Skeleton className="h-4 w-64" />
              </div>
              <Skeleton className="h-6 w-20" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (allTasks.length === 0) {
    return (
      <Card className="md:col-span-2 border-border/40 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base text-foreground">Upcoming Deliverables</CardTitle>
          <CardDescription className="text-sm text-muted-foreground">
            Keep suppliers and banks aligned with a unified schedule.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-sm text-muted-foreground mb-4">No pending tasks at this time.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const getPriorityBadge = (priority: Task["priority"]) => {
    const variants = {
      high: "destructive",
      medium: "secondary",
      low: "outline",
    } as const;
    
    return (
      <Badge variant={variants[priority]} className="text-xs">
        {priority.charAt(0).toUpperCase() + priority.slice(1)}
      </Badge>
    );
  };

  const getDueDateBadge = (dueDate: string) => {
    const due = new Date(dueDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dueDateOnly = new Date(due);
    dueDateOnly.setHours(0, 0, 0, 0);
    
    const diffDays = Math.floor((dueDateOnly.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
      return <Badge variant="destructive" className="text-xs">Overdue</Badge>;
    } else if (diffDays === 0) {
      return <Badge variant="secondary" className="text-xs text-amber-500">Due today</Badge>;
    } else if (diffDays === 1) {
      return <Badge variant="outline" className="text-xs">Tomorrow</Badge>;
    } else if (diffDays <= 7) {
      return <Badge variant="outline" className="text-xs">In {diffDays} days</Badge>;
    } else {
      return <Badge variant="outline" className="text-xs">{due.toLocaleDateString()}</Badge>;
    }
  };

  const getDashboardUrl = (task: Task) => {
    if (task.type === "export") {
      return `/lcopilot/exporter-dashboard?session=${task.lcNumber}`;
    }
    return `/lcopilot/importer-dashboard?session=${task.lcNumber}`;
  };

  return (
    <Card className="md:col-span-2 border-border/40 shadow-sm">
      <CardHeader>
        <CardTitle className="text-base text-foreground">Upcoming Deliverables</CardTitle>
        <CardDescription className="text-sm text-muted-foreground">
          Keep suppliers and banks aligned with a unified schedule.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground">
        {allTasks.map((task) => (
          <div
            key={task.id}
            className="flex items-start justify-between rounded-lg border border-border/40 bg-muted/40 p-4 hover:bg-muted/60 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-foreground font-medium">{task.title}</p>
                {getPriorityBadge(task.priority)}
                <Badge variant="outline" className="text-xs">
                  {task.type === "export" ? "Export" : "Import"}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                {task.description} • LC {task.lcNumber}
              </p>
            </div>
            <div className="flex flex-col items-end gap-2 ml-4">
              {getDueDateBadge(task.dueDate)}
              <Link
                to={getDashboardUrl(task)}
                className="text-xs text-primary hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                View →
              </Link>
            </div>
          </div>
        ))}
        {allTasks.length >= maxItems && (
          <div className="pt-2 border-t">
            <Link
              to="/lcopilot/combined-dashboard?section=workspace"
              className="text-sm text-primary hover:underline"
            >
              View all tasks →
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

