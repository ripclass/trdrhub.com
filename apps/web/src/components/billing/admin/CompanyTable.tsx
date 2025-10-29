/**
 * CompanyTable component - Admin view of all companies with billing info
 */

import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
  Search,
  Filter,
  AlertTriangle,
  Pause,
  Play,
  Edit,
  Mail,
  TrendingUp,
  Building,
  CreditCard
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import {
  PlanType,
  getPlanDisplayName,
  formatCurrency,
  getQuotaThreshold
} from '@/types/billing';
import {
  useAdminCompanyStats,
  useChangeCompanyPlan,
  useUpdateCompanyStatus,
  useSendReminderEmail
} from '@/hooks/useBilling';
import type { AdminCompanyStats } from '@/types/billing';

interface CompanyTableProps {
  className?: string;
  onCompanyClick?: (company: AdminCompanyStats) => void;
  showFilters?: boolean;
}

export function CompanyTable({
  className,
  onCompanyClick,
  showFilters = true
}: CompanyTableProps) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(50);
  const [searchTerm, setSearchTerm] = useState('');
  const [planFilter, setPlanFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Queries and mutations
  const { data: companies, isLoading, refetch } = useAdminCompanyStats(page, perPage);
  const changeCompanyPlan = useChangeCompanyPlan();
  const updateCompanyStatus = useUpdateCompanyStatus();
  const sendReminderEmail = useSendReminderEmail();

  const getPlanIcon = (plan: PlanType) => {
    switch (plan) {
      case PlanType.FREE:
        return '🆓';
      case PlanType.STARTER:
        return '⚡';
      case PlanType.PROFESSIONAL:
        return '👑';
      case PlanType.ENTERPRISE:
        return '🏢';
      default:
        return '📋';
    }
  };

  const getPlanBadgeVariant = (plan: PlanType) => {
    switch (plan) {
      case PlanType.FREE:
        return 'secondary';
      case PlanType.STARTER:
        return 'default';
      case PlanType.PROFESSIONAL:
        return 'default';
      case PlanType.ENTERPRISE:
        return 'default';
      default:
        return 'secondary';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return <Badge variant="default" className="bg-green-100 text-green-800">Active</Badge>;
      case 'suspended':
        return <Badge variant="destructive">Suspended</Badge>;
      case 'overdue':
        return <Badge variant="destructive" className="bg-red-100 text-red-800">Overdue</Badge>;
      case 'cancelled':
        return <Badge variant="secondary" className="bg-gray-100 text-gray-800">Cancelled</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getQuotaUtilizationColor = (used: number, limit: number | null) => {
    if (!limit) return 'text-blue-600'; // Unlimited

    const threshold = getQuotaThreshold(used, limit);
    switch (threshold) {
      case 'exceeded':
        return 'text-red-600 font-semibold';
      case 'critical':
        return 'text-orange-600 font-medium';
      case 'warning':
        return 'text-yellow-600';
      default:
        return 'text-green-600';
    }
  };

  const handlePlanChange = async (companyId: string, newPlan: PlanType) => {
    try {
      await changeCompanyPlan.mutateAsync({ companyId, plan: newPlan });
      refetch();
    } catch (error) {
      console.error('Failed to change plan:', error);
    }
  };

  const handleStatusChange = async (companyId: string, newStatus: string) => {
    try {
      await updateCompanyStatus.mutateAsync({ companyId, status: newStatus });
      refetch();
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  };

  const handleSendReminder = async (companyId: string) => {
    try {
      await sendReminderEmail.mutateAsync(companyId);
    } catch (error) {
      console.error('Failed to send reminder:', error);
    }
  };

  const filteredCompanies = companies?.filter((company) => {
    const matchesSearch = company.company_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesPlan = planFilter === 'all' || company.plan === planFilter;
    const matchesStatus = statusFilter === 'all' || company.status.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesPlan && matchesStatus;
  }) || [];

  const totalPages = Math.ceil(filteredCompanies.length / perPage);
  const startIndex = (page - 1) * perPage;
  const displayedCompanies = filteredCompanies.slice(startIndex, startIndex + perPage);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <div className="w-8 h-8 bg-muted rounded animate-pulse" />
                <div className="space-y-2 flex-1">
                  <div className="h-4 bg-muted rounded animate-pulse" />
                  <div className="h-3 bg-muted rounded animate-pulse w-2/3" />
                </div>
                <div className="w-20 h-4 bg-muted rounded animate-pulse" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <CardTitle className="flex items-center gap-2">
            <Building className="h-5 w-5" />
            Companies
            <Badge variant="secondary">{filteredCompanies.length} companies</Badge>
          </CardTitle>

          {showFilters && (
            <div className="flex items-center space-x-2">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search companies..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8 w-[200px]"
                />
              </div>

              <Select value={planFilter} onValueChange={setPlanFilter}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="All plans" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Plans</SelectItem>
                  <SelectItem value={PlanType.FREE}>Free</SelectItem>
                  <SelectItem value={PlanType.STARTER}>Starter</SelectItem>
                  <SelectItem value={PlanType.PROFESSIONAL}>Professional</SelectItem>
                  <SelectItem value={PlanType.ENTERPRISE}>Enterprise</SelectItem>
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="All status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="suspended">Suspended</SelectItem>
                  <SelectItem value="overdue">Overdue</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearchTerm('');
                  setPlanFilter('all');
                  setStatusFilter('all');
                }}
              >
                <Filter className="h-4 w-4 mr-1" />
                Clear
              </Button>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Company</TableHead>
                <TableHead>Plan</TableHead>
                <TableHead>Usage</TableHead>
                <TableHead>Revenue</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Activity</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayedCompanies.map((company) => (
                <TableRow
                  key={company.company_id}
                  className={cn(
                    'cursor-pointer hover:bg-muted/50',
                    company.status.toLowerCase() === 'overdue' && 'bg-red-50 border-red-200'
                  )}
                  onClick={() => onCompanyClick?.(company)}
                >
                  <TableCell>
                    <div className="flex items-center space-x-3">
                      <div className="text-lg">{getPlanIcon(company.plan)}</div>
                      <div>
                        <div className="font-medium">{company.company_name}</div>
                        <div className="text-sm text-muted-foreground">
                          ID: {company.company_id.slice(-8)}
                        </div>
                      </div>
                      {company.status.toLowerCase() === 'overdue' && (
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                      )}
                    </div>
                  </TableCell>

                  <TableCell>
                    <Badge
                      variant={getPlanBadgeVariant(company.plan)}
                      className="gap-1"
                    >
                      {getPlanDisplayName(company.plan)}
                    </Badge>
                  </TableCell>

                  <TableCell>
                    <div>
                      <div className={cn(
                        'font-medium',
                        getQuotaUtilizationColor(company.quota_used, company.quota_limit)
                      )}>
                        {company.quota_used.toLocaleString()}
                        {company.quota_limit && ` / ${company.quota_limit.toLocaleString()}`}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {company.quota_limit ? (
                          `${Math.round((company.quota_used / company.quota_limit) * 100)}% used`
                        ) : (
                          'Unlimited'
                        )}
                      </div>
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-medium">
                      {formatCurrency(company.total_cost)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {company.total_usage} validations
                    </div>
                  </TableCell>

                  <TableCell>
                    {getStatusBadge(company.status)}
                  </TableCell>

                  <TableCell>
                    <div className="text-sm">
                      {company.last_activity ? (
                        <>
                          <div>{format(new Date(company.last_activity), 'MMM dd')}</div>
                          <div className="text-xs text-muted-foreground">
                            {format(new Date(company.last_activity), 'HH:mm')}
                          </div>
                        </>
                      ) : (
                        <span className="text-muted-foreground">Never</span>
                      )}
                    </div>
                  </TableCell>

                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            onCompanyClick?.(company);
                          }}
                        >
                          <Edit className="h-4 w-4 mr-2" />
                          View Details
                        </DropdownMenuItem>

                        <DropdownMenuSeparator />

                        {/* Plan Change Options */}
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePlanChange(company.company_id, PlanType.STARTER);
                          }}
                          disabled={company.plan === PlanType.STARTER}
                        >
                          <TrendingUp className="h-4 w-4 mr-2" />
                          Upgrade to Starter
                        </DropdownMenuItem>

                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePlanChange(company.company_id, PlanType.PROFESSIONAL);
                          }}
                          disabled={company.plan === PlanType.PROFESSIONAL}
                        >
                          <TrendingUp className="h-4 w-4 mr-2" />
                          Upgrade to Professional
                        </DropdownMenuItem>

                        <DropdownMenuSeparator />

                        {/* Status Management */}
                        {company.status.toLowerCase() === 'active' ? (
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStatusChange(company.company_id, 'suspended');
                            }}
                          >
                            <Pause className="h-4 w-4 mr-2" />
                            Suspend Account
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStatusChange(company.company_id, 'active');
                            }}
                          >
                            <Play className="h-4 w-4 mr-2" />
                            Reactivate Account
                          </DropdownMenuItem>
                        )}

                        {(company.status.toLowerCase() === 'overdue') && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSendReminder(company.company_id);
                              }}
                            >
                              <Mail className="h-4 w-4 mr-2" />
                              Send Payment Reminder
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-4">
            <div className="text-sm text-muted-foreground">
              Showing {startIndex + 1} to {Math.min(startIndex + perPage, filteredCompanies.length)} of{' '}
              {filteredCompanies.length} companies
            </div>

            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>

              <div className="flex items-center space-x-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const pageNum = i + 1;
                  return (
                    <Button
                      key={pageNum}
                      variant={page === pageNum ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setPage(pageNum)}
                      className="w-8 h-8 p-0"
                    >
                      {pageNum}
                    </Button>
                  );
                })}
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page + 1)}
                disabled={page === totalPages}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Summary stats component for the company table
export function CompanyTableSummary({ companies }: { companies?: AdminCompanyStats[] }) {
  if (!companies) return null;

  const totalCompanies = companies.length;
  const activeCompanies = companies.filter(c => c.status.toLowerCase() === 'active').length;
  const overdueCompanies = companies.filter(c => c.status.toLowerCase() === 'overdue').length;
  const totalRevenue = companies.reduce((sum, c) => sum + c.total_cost, 0);

  const planDistribution = companies.reduce((acc, company) => {
    acc[company.plan] = (acc[company.plan] || 0) + 1;
    return acc;
  }, {} as Record<PlanType, number>);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Companies</CardTitle>
          <Building className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{totalCompanies}</div>
          <p className="text-xs text-muted-foreground">
            {activeCompanies} active
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
          <CreditCard className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatCurrency(totalRevenue)}</div>
          <p className="text-xs text-muted-foreground">
            All-time revenue
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Delinquent</CardTitle>
          <AlertTriangle className="h-4 w-4 text-red-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">{overdueCompanies}</div>
          <p className="text-xs text-muted-foreground">
            Need attention
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Enterprise</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{planDistribution[PlanType.ENTERPRISE] || 0}</div>
          <p className="text-xs text-muted-foreground">
            High-value clients
          </p>
        </CardContent>
      </Card>
    </div>
  );
}