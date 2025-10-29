import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  ArrowLeft, 
  BarChart3, 
  TrendingUp, 
  TrendingDown,
  Calendar,
  FileText,
  Clock,
  DollarSign,
  Shield,
  Target,
  Activity,
  PieChart,
  LineChart
} from "lucide-react";

// Mock analytics data
const mockAnalytics = {
  overview: {
    totalLCs: 47,
    monthlyGrowth: 12.5,
    successRate: 94.2,
    avgProcessingTime: "2.3 minutes",
    costSavings: 85000,
    riskMitigation: 92
  },
  monthly: [
    { month: "Jul", lcs: 8, success: 95, avgTime: 2.1 },
    { month: "Aug", lcs: 12, success: 92, avgTime: 2.4 },
    { month: "Sep", lcs: 15, success: 96, avgTime: 2.0 },
    { month: "Oct", lcs: 18, success: 93, avgTime: 2.5 },
    { month: "Nov", lcs: 22, success: 97, avgTime: 1.9 },
    { month: "Dec", lcs: 25, success: 94, avgTime: 2.3 }
  ],
  documentTypes: [
    { type: "Import LC Analysis", count: 28, avgScore: 87, trend: "up" },
    { type: "Supplier Document Check", count: 19, avgScore: 91, trend: "up" },
    { type: "Draft LC Risk Assessment", count: 15, avgScore: 84, trend: "down" },
    { type: "Trade Document Validation", count: 12, avgScore: 89, trend: "up" }
  ],
  riskReduction: [
    { category: "Timeline Risks", reduction: 89, incidents: 3 },
    { category: "Documentation Risks", reduction: 94, incidents: 2 },
    { category: "Compliance Risks", reduction: 92, incidents: 1 },
    { category: "Financial Risks", reduction: 87, incidents: 4 }
  ]
};

export default function ImporterAnalytics() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-gray-200">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/importer-dashboard">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Dashboard
                </Button>
              </Link>
              <div className="flex items-center gap-3">
                <div className="bg-gradient-primary p-2 rounded-lg">
                  <BarChart3 className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-foreground">Importer Analytics</h1>
                  <p className="text-sm text-muted-foreground">Performance insights and trends</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Key Metrics Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total LCs Processed</p>
                  <p className="text-2xl font-bold text-foreground">{mockAnalytics.overview.totalLCs}</p>
                  <div className="flex items-center gap-1 mt-1">
                    <TrendingUp className="w-4 h-4 text-success" />
                    <span className="text-sm text-success">+{mockAnalytics.overview.monthlyGrowth}% this month</span>
                  </div>
                </div>
                <div className="bg-importer/10 p-3 rounded-lg">
                  <FileText className="w-6 h-6 text-importer" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Success Rate</p>
                  <p className="text-2xl font-bold text-foreground">{mockAnalytics.overview.successRate}%</p>
                  <div className="flex items-center gap-1 mt-1">
                    <TrendingUp className="w-4 h-4 text-success" />
                    <span className="text-sm text-success">Above industry average</span>
                  </div>
                </div>
                <div className="bg-success/10 p-3 rounded-lg">
                  <Target className="w-6 h-6 text-success" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Avg Processing Time</p>
                  <p className="text-2xl font-bold text-foreground">{mockAnalytics.overview.avgProcessingTime}</p>
                  <div className="flex items-center gap-1 mt-1">
                    <TrendingDown className="w-4 h-4 text-success" />
                    <span className="text-sm text-success">15% faster than before</span>
                  </div>
                </div>
                <div className="bg-primary/10 p-3 rounded-lg">
                  <Clock className="w-6 h-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Analytics Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="insights">Insights</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Cost Impact */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <DollarSign className="w-5 h-5" />
                    Financial Impact
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-success mb-2">
                      ${mockAnalytics.overview.costSavings.toLocaleString()}
                    </div>
                    <p className="text-sm text-muted-foreground">Total cost savings this year</p>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span>Reduced processing delays</span>
                      <span className="font-medium text-success">$35,000</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Avoided document rejections</span>
                      <span className="font-medium text-success">$28,000</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Faster customs clearance</span>
                      <span className="font-medium text-success">$22,000</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Risk Mitigation */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="w-5 h-5" />
                    Risk Mitigation
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-importer mb-2">
                      {mockAnalytics.overview.riskMitigation}%
                    </div>
                    <p className="text-sm text-muted-foreground">Overall risk reduction achieved</p>
                  </div>
                  
                  <div className="space-y-3">
                    {mockAnalytics.riskReduction.map((risk, index) => (
                      <div key={index} className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>{risk.category}</span>
                          <span className="font-medium">{risk.reduction}%</span>
                        </div>
                        <Progress value={risk.reduction} className="h-2" />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="trends" className="space-y-6">
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LineChart className="w-5 h-5" />
                  Monthly Trends
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {mockAnalytics.monthly.map((month, index) => (
                    <div key={index} className="grid grid-cols-4 gap-4 p-3 rounded-lg bg-muted/30">
                      <div className="text-center">
                        <div className="text-sm text-muted-foreground">Month</div>
                        <div className="font-medium">{month.month}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-muted-foreground">LCs Processed</div>
                        <div className="font-medium text-importer">{month.lcs}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-muted-foreground">Success Rate</div>
                        <div className="font-medium text-success">{month.success}%</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-muted-foreground">Avg Time</div>
                        <div className="font-medium">{month.avgTime}m</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="performance" className="space-y-6">
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  Document Type Performance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {mockAnalytics.documentTypes.map((doc, index) => (
                    <div key={index} className="flex items-center justify-between p-4 rounded-lg border border-gray-200">
                      <div className="flex-1">
                        <div className="font-medium">{doc.type}</div>
                        <div className="text-sm text-muted-foreground">{doc.count} documents processed</div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-center">
                          <div className="text-sm text-muted-foreground">Avg Score</div>
                          <div className="font-medium">{doc.avgScore}%</div>
                        </div>
                        <div className="flex items-center gap-1">
                          {doc.trend === "up" ? (
                            <TrendingUp className="w-4 h-4 text-success" />
                          ) : (
                            <TrendingDown className="w-4 h-4 text-destructive" />
                          )}
                          <span className={`text-sm ${doc.trend === "up" ? "text-success" : "text-destructive"}`}>
                            {doc.trend === "up" ? "Improving" : "Declining"}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="insights" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle>Key Insights</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-3 bg-success/5 border border-success/20 rounded-lg">
                    <p className="text-sm font-medium text-success mb-1">📈 Efficiency Gains</p>
                    <p className="text-xs text-muted-foreground">
                      Your processing efficiency has improved by 23% over the last quarter, with particularly strong performance in supplier document validation.
                    </p>
                  </div>
                  
                  <div className="p-3 bg-importer/5 border border-importer/20 rounded-lg">
                    <p className="text-sm font-medium text-importer mb-1">🎯 Risk Management</p>
                    <p className="text-xs text-muted-foreground">
                      Successfully identified and mitigated 15 high-risk scenarios, preventing potential financial losses of approximately $45,000.
                    </p>
                  </div>
                  
                  <div className="p-3 bg-warning/5 border border-warning/20 rounded-lg">
                    <p className="text-sm font-medium text-warning mb-1">⚠️ Areas for Improvement</p>
                    <p className="text-xs text-muted-foreground">
                      Draft LC risk assessments show room for improvement. Consider more detailed supplier vetting processes.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle>Recommendations</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="p-3 rounded-lg border border-gray-200">
                      <p className="text-sm font-medium mb-1">Optimize Timeline Management</p>
                      <p className="text-xs text-muted-foreground">
                        Consider extending LC negotiation periods by 2-3 days to reduce timeline-related risks.
                      </p>
                    </div>
                    
                    <div className="p-3 rounded-lg border border-gray-200">
                      <p className="text-sm font-medium mb-1">Supplier Performance Tracking</p>
                      <p className="text-xs text-muted-foreground">
                        Implement regular supplier compliance scoring to predict and prevent document issues.
                      </p>
                    </div>
                    
                    <div className="p-3 rounded-lg border border-gray-200">
                      <p className="text-sm font-medium mb-1">Automated Notifications</p>
                      <p className="text-xs text-muted-foreground">
                        Set up alerts for critical compliance deadlines to maintain your excellent success rate.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}