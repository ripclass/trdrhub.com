import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getUserSessions, ValidationSession } from "@/api/sessions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { StatusBadge } from "@/components/ui/status-badge";
import { 
  FileText, 
  Upload, 
  TrendingUp, 
  Clock, 
  AlertTriangle, 
  Download,
  Bell,
  Settings,
  LogOut,
  User,
  Plus,
  BarChart3,
  CheckCircle,
  XCircle
} from "lucide-react";

// State interface for dashboard data
interface DashboardStats {
  totalLCs: number;
  thisMonth: number;
  successRate: number;
  avgProcessingTime: string;
  discrepanciesFound: number;
  documentsProcessed: number;
}

interface RecentLC {
  id: string;
  lcNumber: string;
  companyName: string;
  dateProcessed: string;
  status: "success" | "error" | "warning" | "pending";
  discrepancies: number;
  documentsCount: number;
  downloadUrl: string;
}

const recentLCs = [
  {
    id: "LC001",
    lcNumber: "BD-2024-001",
    companyName: "Dhaka Exports Ltd",
    dateProcessed: "2024-01-15",
    status: "success" as const,
    discrepancies: 0,
    documentsCount: 5,
    downloadUrl: "#"
  },
  {
    id: "LC002", 
    lcNumber: "BD-2024-002",
    companyName: "Bengal Trade Co",
    dateProcessed: "2024-01-14",
    status: "error" as const,
    discrepancies: 3,
    documentsCount: 7,
    downloadUrl: "#"
  },
  {
    id: "LC003",
    lcNumber: "BD-2024-003", 
    companyName: "Chittagong Imports",
    dateProcessed: "2024-01-14",
    status: "warning" as const,
    discrepancies: 1,
    documentsCount: 4,
    downloadUrl: "#"
  },
  {
    id: "LC004",
    lcNumber: "BD-2024-004",
    companyName: "Sylhet Textiles",
    dateProcessed: "2024-01-13",
    status: "success" as const,
    discrepancies: 0,
    documentsCount: 6,
    downloadUrl: "#"
  }
];

const notifications = [
  {
    id: 1,
    title: "New ICC Update Available",
    message: "UCP 600 guidelines have been updated. Review new discrepancy rules.",
    type: "info" as const,
    timestamp: "2 hours ago"
  },
  {
    id: 2,
    title: "LC Processing Complete",
    message: "BD-2024-005 has been processed successfully with no discrepancies.",
    type: "success" as const,
    timestamp: "4 hours ago"
  },
  {
    id: 3,
    title: "Discrepancy Alert",
    message: "BD-2024-006 has 2 discrepancies that need attention.",
    type: "warning" as const,
    timestamp: "1 day ago"
  }
];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const [sessions, setSessions] = useState<ValidationSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [dashboardStats, setDashboardStats] = useState<DashboardStats>({
    totalLCs: 0,
    thisMonth: 0,
    successRate: 0,
    avgProcessingTime: "0 minutes",
    discrepanciesFound: 0,
    documentsProcessed: 0
  });
  const [recentLCs, setRecentLCs] = useState<RecentLC[]>([]);

  // Transform sessions to dashboard data
  const transformSessionsToStats = (sessions: ValidationSession[]): { stats: DashboardStats, recent: RecentLC[] } => {
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    const completedSessions = sessions.filter(s => s.status === 'completed');
    const thisMonthSessions = completedSessions.filter(s => {
      const sessionDate = new Date(s.created_at);
      return sessionDate.getMonth() === currentMonth && sessionDate.getFullYear() === currentYear;
    });

    const totalDiscrepancies = completedSessions.reduce((sum, s) => sum + s.discrepancies.length, 0);
    const totalDocuments = completedSessions.reduce((sum, s) => sum + s.documents.length, 0);
    const successCount = completedSessions.filter(s => s.discrepancies.length === 0).length;
    const successRate = completedSessions.length > 0 ? (successCount / completedSessions.length) * 100 : 0;

    // Calculate real average processing time from session timestamps
    const sessionsWithTime = completedSessions.filter(s => s.processing_started_at && s.processing_completed_at);
    const avgProcessingMs = sessionsWithTime.length > 0
      ? sessionsWithTime.reduce((sum, s) => {
          const start = new Date(s.processing_started_at!).getTime();
          const end = new Date(s.processing_completed_at!).getTime();
          return sum + (end - start);
        }, 0) / sessionsWithTime.length
      : 0;
    const avgProcessingTime = avgProcessingMs > 0 
      ? `${(avgProcessingMs / 60000).toFixed(1)} min`
      : "N/A";

    const stats: DashboardStats = {
      totalLCs: sessions.length,
      thisMonth: thisMonthSessions.length,
      successRate: Math.round(successRate * 10) / 10,
      avgProcessingTime,
      discrepanciesFound: totalDiscrepancies,
      documentsProcessed: totalDocuments
    };

    const recent: RecentLC[] = sessions
      .slice(0, 4)
      .map((session) => ({
        id: session.id,
        lcNumber: session.extracted_data?.lc_number || `LC-${session.id.slice(-6)}`,
        companyName: session.extracted_data?.beneficiary_name || session.extracted_data?.applicant || "Unknown",
        dateProcessed: new Date(session.created_at).toISOString().split('T')[0],
        status: session.status === 'completed'
               ? (session.discrepancies.length === 0 ? "success" :
                  session.discrepancies.length > 2 ? "error" : "warning")
               : "pending",
        discrepancies: session.discrepancies.length,
        documentsCount: session.documents.length,
        downloadUrl: `/lcopilot/report/${session.id}`
      }));

    return { stats, recent };
  };

  // Load sessions on mount
  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        const userSessions = await getUserSessions();
        setSessions(userSessions);

        const { stats, recent } = transformSessionsToStats(userSessions);
        setDashboardStats(stats);
        setRecentLCs(recent);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
        // Keep default empty state
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-gray-200 sticky top-0 z-50 backdrop-blur-sm bg-card/95">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="bg-gradient-primary p-2 rounded-lg">
                  <FileText className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-foreground">LCopilot</h1>
                  <p className="text-sm text-muted-foreground">Dashboard</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Button variant="outline" size="sm">
                <Bell className="w-4 h-4 mr-2" />
                Notifications
                <Badge variant="destructive" className="ml-2 h-5 w-5 p-0 text-xs">3</Badge>
              </Button>
              <Button variant="outline" size="sm">
                <User className="w-4 h-4 mr-2" />
                Profile
              </Button>
              <Button variant="outline" size="sm">
                <Settings className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-foreground mb-2">
            Welcome back, Bangladesh Exports Ltd
          </h2>
          <p className="text-muted-foreground">
            Here's what's happening with your LC validations today.
          </p>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <Link to="/upload" className="flex-1">
            <Button className="w-full h-16 bg-gradient-primary hover:opacity-90 text-left justify-start shadow-medium group">
              <div className="flex items-center gap-4">
                <div className="bg-white/20 p-3 rounded-lg group-hover:scale-110 transition-transform">
                  <Plus className="w-6 h-6" />
                </div>
                <div>
                  <div className="font-semibold">Upload New LC</div>
                  <div className="text-sm opacity-90">Start validation process</div>
                </div>
              </div>
            </Button>
          </Link>
          <Button variant="outline" className="flex-1 h-16 text-left justify-start">
            <div className="flex items-center gap-4">
              <div className="bg-primary/10 p-3 rounded-lg">
                <BarChart3 className="w-6 h-6 text-primary" />
              </div>
              <div>
                <div className="font-semibold">View Analytics</div>
                <div className="text-sm text-muted-foreground">Performance insights</div>
              </div>
            </div>
          </Button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">This Month</p>
                  <p className="text-2xl font-bold text-foreground">{dashboardStats.thisMonth}</p>
                  <p className="text-xs text-success">+18% from last month</p>
                </div>
                <div className="bg-primary/10 p-3 rounded-lg">
                  <FileText className="w-6 h-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Success Rate</p>
                  <p className="text-2xl font-bold text-foreground">{dashboardStats.successRate}%</p>
                  <Progress value={dashboardStats.successRate} className="mt-2 h-2" />
                </div>
                <div className="bg-success/10 p-3 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-success" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Avg Processing</p>
                  <p className="text-2xl font-bold text-foreground">{dashboardStats.avgProcessingTime}</p>
                  <p className="text-xs text-success">15s faster</p>
                </div>
                <div className="bg-info/10 p-3 rounded-lg">
                  <Clock className="w-6 h-6 text-info" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Discrepancies</p>
                  <p className="text-2xl font-bold text-foreground">{dashboardStats.discrepanciesFound}</p>
                  <p className="text-xs text-warning">Needs attention</p>
                </div>
                <div className="bg-warning/10 p-3 rounded-lg">
                  <AlertTriangle className="w-6 h-6 text-warning" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Recent LCs */}
          <div className="lg:col-span-2">
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Recent LC Validations
                </CardTitle>
                <CardDescription>
                  Your latest document validation results
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recentLCs.map((lc) => (
                    <div key={lc.id} className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50">
                      <div className="flex items-center gap-4">
                        <div className="flex-shrink-0">
                          {lc.status === "success" ? (
                            <div className="bg-success/10 p-2 rounded-lg">
                              <CheckCircle className="w-5 h-5 text-success" />
                            </div>
                          ) : lc.status === "error" ? (
                            <div className="bg-destructive/10 p-2 rounded-lg">
                              <XCircle className="w-5 h-5 text-destructive" />
                            </div>
                          ) : (
                            <div className="bg-warning/10 p-2 rounded-lg">
                              <AlertTriangle className="w-5 h-5 text-warning" />
                            </div>
                          )}
                        </div>
                        <div>
                          <h4 className="font-semibold text-foreground">{lc.lcNumber}</h4>
                          <p className="text-sm text-muted-foreground">{lc.companyName}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-muted-foreground">{lc.dateProcessed}</span>
                            <span className="text-xs text-muted-foreground">•</span>
                            <span className="text-xs text-muted-foreground">{lc.documentsCount} documents</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <StatusBadge status={lc.status}>
                            {lc.discrepancies === 0 ? "No Issues" : `${lc.discrepancies} Issues`}
                          </StatusBadge>
                        </div>
                        <Button variant="outline" size="sm">
                          <Download className="w-4 h-4 mr-2" />
                          Download
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-6 text-center">
                  <Button variant="outline">View All LCs</Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Notifications */}
          <div>
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="w-5 h-5" />
                  Notifications
                </CardTitle>
                <CardDescription>
                  Updates and alerts
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {notifications.map((notification) => (
                    <div key={notification.id} className="p-3 border border-gray-200/50 rounded-lg">
                      <div className="flex items-start gap-3">
                        <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                          notification.type === "success" ? "bg-success" :
                          notification.type === "warning" ? "bg-warning" :
                          notification.type === "info" ? "bg-info" : "bg-destructive"
                        }`} />
                        <div className="flex-1 min-w-0">
                          <h5 className="font-medium text-sm text-foreground">{notification.title}</h5>
                          <p className="text-xs text-muted-foreground mt-1">{notification.message}</p>
                          <p className="text-xs text-muted-foreground/70 mt-2">{notification.timestamp}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-4">
                  <Button variant="outline" size="sm" className="w-full">
                    View All Notifications
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Quick Stats */}
            <Card className="shadow-soft border-0 mt-6">
              <CardHeader>
                <CardTitle className="text-base">Quick Stats</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Total LCs</span>
                  <span className="font-semibold">{dashboardStats.totalLCs}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Documents Processed</span>
                  <span className="font-semibold">{dashboardStats.documentsProcessed}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">API Credits Used</span>
                  <span className="font-semibold text-primary">245 / 1000</span>
                </div>
                <Progress value={24.5} className="h-2" />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}