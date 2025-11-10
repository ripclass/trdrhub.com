import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useQuery } from "@tanstack/react-query";
import { bankApi, ClientStats, BankResult } from "@/api/bank";
import { format } from "date-fns";
import { Search, Users, CheckCircle, XCircle, AlertCircle, TrendingUp, TrendingDown, FileText, ExternalLink, BarChart3, Activity, Copy, Clock, ArrowUp, ArrowDown, ChevronDown, ChevronRight } from "lucide-react";
import { sanitizeText } from "@/lib/sanitize";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";
import { ClientDetailView } from "./ClientDetailView";

interface ClientManagementProps {}

export function ClientManagement({}: ClientManagementProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedClients, setExpandedClients] = useState<Set<string>>(new Set());
  const itemsPerPage = 20;
  const { toast } = useToast();
  const navigate = useNavigate();

  const toggleClientExpansion = (clientName: string) => {
    setExpandedClients(prev => {
      const next = new Set(prev);
      if (next.has(clientName)) {
        next.delete(clientName);
      } else {
        next.add(clientName);
      }
      return next;
    });
  };

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['bank-client-stats', searchQuery, currentPage],
    queryFn: () => bankApi.getClientStats({
      query: searchQuery || undefined,
      limit: itemsPerPage,
      offset: (currentPage - 1) * itemsPerPage,
    }),
    staleTime: 30 * 1000, // Cache for 30 seconds
  });

  const handleViewResults = (clientName: string) => {
    // Navigate to Results tab with client filter applied
    navigate('/lcopilot/bank-dashboard?tab=results&client=' + encodeURIComponent(clientName));
  };

  const handleViewDashboard = (clientName: string) => {
    // Navigate to client dashboard tab within Bank Dashboard V2
    navigate(`/lcopilot/bank-dashboard?tab=client-dashboard&client=${encodeURIComponent(clientName)}`);
  };

  const getStatusBadge = (stats: ClientStats) => {
    if (stats.compliance_rate >= 90) {
      return (
        <Badge variant="default" className="bg-green-600">
          <CheckCircle className="w-3 h-3 mr-1" />
          Excellent
        </Badge>
      );
    } else if (stats.compliance_rate >= 75) {
      return (
        <Badge variant="secondary" className="bg-yellow-600">
          <AlertCircle className="w-3 h-3 mr-1" />
          Good
        </Badge>
      );
    } else {
      return (
        <Badge variant="destructive">
          <XCircle className="w-3 h-3 mr-1" />
          Needs Attention
        </Badge>
      );
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Client Management</CardTitle>
          <CardDescription>Loading client statistics...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4 animate-pulse" />
            <p className="text-muted-foreground">Loading clients...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Client Management</CardTitle>
          <CardDescription>Error loading client statistics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 mx-auto text-destructive mb-4" />
            <p className="text-destructive">Failed to load client data</p>
            <Button onClick={() => refetch()} className="mt-4">
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const clients = data?.clients || [];
  const totalClients = data?.total || 0;
  const totalPages = Math.ceil(totalClients / itemsPerPage);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Client Management
            </CardTitle>
            <CardDescription>
              View and manage client validation statistics
            </CardDescription>
          </div>
          <Badge variant="outline" className="text-sm">
            {totalClients} {totalClients === 1 ? 'Client' : 'Clients'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              placeholder="Search clients by name..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1); // Reset to first page on search
              }}
              className="pl-10"
            />
          </div>
        </div>

        {/* Summary Stats */}
        {clients.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Clients</p>
                    <p className="text-2xl font-bold">{totalClients}</p>
                  </div>
                  <Users className="w-8 h-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Validations</p>
                    <p className="text-2xl font-bold">
                      {clients.reduce((sum, c) => sum + c.total_validations, 0).toLocaleString()}
                    </p>
                  </div>
                  <FileText className="w-8 h-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Avg Compliance</p>
                    <p className="text-2xl font-bold">
                      {clients.length > 0
                        ? Math.round(
                            clients.reduce((sum, c) => sum + c.compliance_rate, 0) / clients.length
                          )
                        : 0}
                      %
                    </p>
                  </div>
                  <TrendingUp className="w-8 h-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Discrepancies</p>
                    <p className="text-2xl font-bold">
                      {clients.reduce((sum, c) => sum + c.total_discrepancies, 0).toLocaleString()}
                    </p>
                  </div>
                  <AlertCircle className="w-8 h-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Client Table */}
        {clients.length === 0 ? (
          <div className="text-center py-12">
            <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              {searchQuery
                ? `No clients found matching "${sanitizeText(searchQuery)}"`
                : "No clients found. Upload LC validations to see client statistics."}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 font-semibold">Client Name</th>
                    <th className="text-right p-3 font-semibold">Validations</th>
                    <th className="text-right p-3 font-semibold">Compliant</th>
                    <th className="text-right p-3 font-semibold">Discrepancies</th>
                    <th className="text-right p-3 font-semibold">Failed</th>
                    <th className="text-right p-3 font-semibold">Avg Score</th>
                    <th className="text-right p-3 font-semibold">Compliance Rate</th>
                    <th className="text-left p-3 font-semibold">Last Validation</th>
                    <th className="text-center p-3 font-semibold">Status</th>
                    <th className="text-center p-3 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {clients.map((client) => {
                    const isExpanded = expandedClients.has(client.client_name);
                    return (
                      <React.Fragment key={client.client_name}>
                        <tr className="border-b hover:bg-muted/50 cursor-pointer" onClick={() => toggleClientExpansion(client.client_name)}>
                          <td className="p-3 font-medium">
                            <div className="flex items-center gap-2">
                              {isExpanded ? (
                                <ChevronDown className="w-4 h-4 text-muted-foreground" />
                              ) : (
                                <ChevronRight className="w-4 h-4 text-muted-foreground" />
                              )}
                              {sanitizeText(client.client_name)}
                            </div>
                          </td>
                          <td className="p-3 text-right">
                            {client.total_validations.toLocaleString()}
                          </td>
                          <td className="p-3 text-right">
                            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                              {client.compliant_count}
                            </Badge>
                          </td>
                          <td className="p-3 text-right">
                            {client.discrepancies_count > 0 ? (
                              <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
                                {client.discrepancies_count}
                              </Badge>
                            ) : (
                              <span className="text-muted-foreground">0</span>
                            )}
                          </td>
                          <td className="p-3 text-right">
                            {client.failed_count > 0 ? (
                              <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                                {client.failed_count}
                              </Badge>
                            ) : (
                              <span className="text-muted-foreground">0</span>
                            )}
                          </td>
                          <td className="p-3 text-right font-medium">
                            {client.average_compliance_score.toFixed(1)}%
                          </td>
                          <td className="p-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <span className="font-medium">{client.compliance_rate.toFixed(1)}%</span>
                              <div className="w-16 bg-muted rounded-full h-2">
                                <div
                                  className={`h-2 rounded-full ${
                                    client.compliance_rate >= 90
                                      ? "bg-green-600"
                                      : client.compliance_rate >= 75
                                      ? "bg-yellow-600"
                                      : "bg-red-600"
                                  }`}
                                  style={{ width: `${client.compliance_rate}%` }}
                                />
                              </div>
                            </div>
                          </td>
                          <td className="p-3 text-left text-muted-foreground">
                            {client.last_validation_date
                              ? format(new Date(client.last_validation_date), "MMM d, yyyy")
                              : "N/A"}
                          </td>
                          <td className="p-3 text-center">
                            {getStatusBadge(client)}
                          </td>
                          <td className="p-3 text-center" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-center gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleViewDashboard(client.client_name)}
                                className="h-8"
                              >
                                <BarChart3 className="w-4 h-4 mr-1" />
                                Dashboard
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleViewResults(client.client_name)}
                                className="h-8"
                              >
                                <ExternalLink className="w-4 h-4 mr-1" />
                                Results
                              </Button>
                            </div>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr>
                            <td colSpan={10} className="p-0">
                              <ClientDetailView
                                clientName={client.client_name}
                                clientStats={{
                                  total_validations: client.total_validations,
                                  compliance_rate: client.compliance_rate,
                                  average_compliance_score: client.average_compliance_score,
                                  total_discrepancies: client.total_discrepancies,
                                  discrepancies_count: client.discrepancies_count,
                                  compliant_count: client.compliant_count,
                                  failed_count: client.failed_count,
                                }}
                              />
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6">
                <div className="text-sm text-muted-foreground">
                  Showing {((currentPage - 1) * itemsPerPage) + 1} to{" "}
                  {Math.min(currentPage * itemsPerPage, totalClients)} of {totalClients} clients
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </Button>
                  <div className="text-sm text-muted-foreground">
                    Page {currentPage} of {totalPages}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

