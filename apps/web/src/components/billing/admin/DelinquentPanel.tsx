/**
 * DelinquentPanel component - Manages overdue accounts and payment issues
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertTriangle,
  CreditCard,
  Mail,
  Phone,
  MoreHorizontal,
  Clock,
  XCircle,
  DollarSign,
  Building,
  Calendar,
  Pause,
  Play
} from 'lucide-react';
import { format, differenceInDays } from 'date-fns';
// Inline cn function to avoid import/bundling issues
function cn(...classes: (string | undefined | null | boolean | Record<string, boolean>)[]): string {
  return classes
    .filter(Boolean)
    .map((cls) => {
      if (typeof cls === 'string') return cls;
      if (typeof cls === 'object' && cls !== null) {
        return Object.entries(cls)
          .filter(([_, val]) => val)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join(' ');
}
;

// Hooks and types
import {
  useAdminCompanyStats,
  useInvoices,
  useRetryPayment,
  useSendReminderEmail,
  useUpdateCompanyStatus
} from '@/hooks/useBilling';
import { formatCurrency, getInvoiceStatusColor } from '@/types/billing';
import type { AdminCompanyStats, Invoice, InvoiceStatus } from '@/types/billing';

interface DelinquentPanelProps {
  className?: string;
  onCompanyClick?: (company: AdminCompanyStats) => void;
  maxItems?: number;
}

export function DelinquentPanel({
  className,
  onCompanyClick,
  maxItems = 10
}: DelinquentPanelProps) {
  const [activeTab, setActiveTab] = useState<'overdue' | 'failed' | 'suspended'>('overdue');

  // Queries
  const { data: companies } = useAdminCompanyStats(1, 100);
  const { data: invoicesData } = useInvoices({ status: 'OVERDUE', per_page: 50 });

  // Mutations
  const retryPayment = useRetryPayment();
  const sendReminderEmail = useSendReminderEmail();
  const updateCompanyStatus = useUpdateCompanyStatus();

  // Filter companies by delinquent status
  const overdueCompanies = companies?.filter(c => c.status.toLowerCase() === 'overdue') || [];
  const suspendedCompanies = companies?.filter(c => c.status.toLowerCase() === 'suspended') || [];

  // Mock failed payment invoices (would come from API)
  const failedInvoices: Invoice[] = [
    {
      id: '1',
      company_id: 'comp1',
      invoice_number: 'INV-2024-001',
      amount: 45000,
      currency: 'BDT',
      status: 'FAILED' as InvoiceStatus,
      issued_date: '2024-01-15',
      due_date: '2024-02-15',
      paid_date: null,
      payment_intent_id: 'pi_failed_123',
      payment_method: null,
      description: 'Monthly subscription',
      line_items: [],
      created_at: '2024-01-15T10:00:00Z',
      updated_at: null
    }
  ];

  const getCompanyInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getOverdueDays = (dueDate: string) => {
    return differenceInDays(new Date(), new Date(dueDate));
  };

  const getSeverityColor = (days: number) => {
    if (days > 30) return 'text-red-600 bg-red-100';
    if (days > 14) return 'text-orange-600 bg-orange-100';
    return 'text-yellow-600 bg-yellow-100';
  };

  const handleRetryPayment = async (invoiceId: string) => {
    try {
      await retryPayment.mutateAsync({ invoiceId });
    } catch (error) {
      console.error('Failed to retry payment:', error);
    }
  };

  const handleSendReminder = async (companyId: string) => {
    try {
      await sendReminderEmail.mutateAsync(companyId);
    } catch (error) {
      console.error('Failed to send reminder:', error);
    }
  };

  const handleSuspendCompany = async (companyId: string) => {
    try {
      await updateCompanyStatus.mutateAsync({ companyId, status: 'suspended' });
    } catch (error) {
      console.error('Failed to suspend company:', error);
    }
  };

  const handleReactivateCompany = async (companyId: string) => {
    try {
      await updateCompanyStatus.mutateAsync({ companyId, status: 'active' });
    } catch (error) {
      console.error('Failed to reactivate company:', error);
    }
  };

  const getCurrentTabData = () => {
    switch (activeTab) {
      case 'overdue':
        return overdueCompanies.slice(0, maxItems);
      case 'failed':
        return failedInvoices.slice(0, maxItems);
      case 'suspended':
        return suspendedCompanies.slice(0, maxItems);
      default:
        return [];
    }
  };

  const getCurrentTabCount = () => {
    switch (activeTab) {
      case 'overdue':
        return overdueCompanies.length;
      case 'failed':
        return failedInvoices.length;
      case 'suspended':
        return suspendedCompanies.length;
      default:
        return 0;
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            Delinquent Accounts
          </CardTitle>

          <div className="flex items-center space-x-1">
            <Button
              size="sm"
              variant={activeTab === 'overdue' ? 'default' : 'outline'}
              onClick={() => setActiveTab('overdue')}
              className="gap-1"
            >
              <Clock className="h-3 w-3" />
              Overdue
              {overdueCompanies.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {overdueCompanies.length}
                </Badge>
              )}
            </Button>

            <Button
              size="sm"
              variant={activeTab === 'failed' ? 'default' : 'outline'}
              onClick={() => setActiveTab('failed')}
              className="gap-1"
            >
              <XCircle className="h-3 w-3" />
              Failed
              {failedInvoices.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {failedInvoices.length}
                </Badge>
              )}
            </Button>

            <Button
              size="sm"
              variant={activeTab === 'suspended' ? 'default' : 'outline'}
              onClick={() => setActiveTab('suspended')}
              className="gap-1"
            >
              <Pause className="h-3 w-3" />
              Suspended
              {suspendedCompanies.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {suspendedCompanies.length}
                </Badge>
              )}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {getCurrentTabCount() === 0 ? (
          <div className="text-center py-8">
            <div className="text-muted-foreground mb-2">
              {activeTab === 'overdue' && 'No overdue accounts'}
              {activeTab === 'failed' && 'No failed payments'}
              {activeTab === 'suspended' && 'No suspended accounts'}
            </div>
            <p className="text-sm text-green-600">All accounts are in good standing! 🎉</p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Overdue Companies */}
            {activeTab === 'overdue' && overdueCompanies.slice(0, maxItems).map((company) => {
              const overdueDays = getOverdueDays(new Date().toISOString()); // Mock due date

              return (
                <div
                  key={company.company_id}
                  className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors cursor-pointer"
                  onClick={() => onCompanyClick?.(company)}
                >
                  <div className="flex items-center space-x-3">
                    <Avatar className="h-10 w-10">
                      <AvatarFallback className="bg-red-100 text-red-600">
                        {getCompanyInitials(company.company_name)}
                      </AvatarFallback>
                    </Avatar>

                    <div>
                      <div className="font-medium">{company.company_name}</div>
                      <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                        <DollarSign className="h-3 w-3" />
                        <span>{formatCurrency(company.total_cost)}</span>
                        <Badge className={cn('text-xs', getSeverityColor(overdueDays))}>
                          {overdueDays} days overdue
                        </Badge>
                      </div>
                    </div>
                  </div>

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
                          handleSendReminder(company.company_id);
                        }}
                      >
                        <Mail className="h-4 w-4 mr-2" />
                        Send Reminder
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          // Open phone/call interface
                        }}
                      >
                        <Phone className="h-4 w-4 mr-2" />
                        Call Company
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSuspendCompany(company.company_id);
                        }}
                        className="text-red-600"
                      >
                        <Pause className="h-4 w-4 mr-2" />
                        Suspend Account
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              );
            })}

            {/* Failed Payment Invoices */}
            {activeTab === 'failed' && failedInvoices.slice(0, maxItems).map((invoice) => (
              <div
                key={invoice.id}
                className="flex items-center justify-between p-3 bg-orange-50 border border-orange-200 rounded-lg hover:bg-orange-100 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-orange-100 rounded-full">
                    <XCircle className="h-4 w-4 text-orange-600" />
                  </div>

                  <div>
                    <div className="font-medium">{invoice.invoice_number}</div>
                    <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                      <span>{formatCurrency(invoice.amount, invoice.currency)}</span>
                      <Badge variant="destructive" className="text-xs">
                        Payment Failed
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Due: {format(new Date(invoice.due_date), 'MMM dd, yyyy')}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRetryPayment(invoice.id)}
                    disabled={retryPayment.isPending}
                    className="gap-1"
                  >
                    <CreditCard className="h-3 w-3" />
                    Retry
                  </Button>
                </div>
              </div>
            ))}

            {/* Suspended Companies */}
            {activeTab === 'suspended' && suspendedCompanies.slice(0, maxItems).map((company) => (
              <div
                key={company.company_id}
                className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                onClick={() => onCompanyClick?.(company)}
              >
                <div className="flex items-center space-x-3">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className="bg-gray-100 text-gray-600">
                      {getCompanyInitials(company.company_name)}
                    </AvatarFallback>
                  </Avatar>

                  <div>
                    <div className="font-medium text-gray-600">{company.company_name}</div>
                    <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                      <Building className="h-3 w-3" />
                      <span>{company.total_usage} validations</span>
                      <Badge variant="secondary" className="text-xs">
                        Suspended
                      </Badge>
                    </div>
                    {company.last_activity && (
                      <div className="text-xs text-muted-foreground">
                        Last active: {format(new Date(company.last_activity), 'MMM dd, yyyy')}
                      </div>
                    )}
                  </div>
                </div>

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
                        handleReactivateCompany(company.company_id);
                      }}
                      className="text-green-600"
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Reactivate Account
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={(e) => {
                        e.stopPropagation();
                        onCompanyClick?.(company);
                      }}
                    >
                      <Building className="h-4 w-4 mr-2" />
                      View Details
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ))}
          </div>
        )}

        {/* Show more button if there are more items */}
        {getCurrentTabCount() > maxItems && (
          <div className="text-center pt-4 border-t">
            <Button variant="outline" size="sm">
              View All {getCurrentTabCount() - maxItems} More
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Summary component for delinquent accounts
export function DelinquentSummary({ companies }: { companies?: AdminCompanyStats[] }) {
  if (!companies) return null;

  const overdueCount = companies.filter(c => c.status.toLowerCase() === 'overdue').length;
  const suspendedCount = companies.filter(c => c.status.toLowerCase() === 'suspended').length;
  const totalDelinquent = overdueCount + suspendedCount;

  const overdueRevenue = companies
    .filter(c => c.status.toLowerCase() === 'overdue')
    .reduce((sum, c) => sum + c.total_cost, 0);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Delinquent</CardTitle>
          <AlertTriangle className="h-4 w-4 text-red-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">{totalDelinquent}</div>
          <p className="text-xs text-muted-foreground">
            {((totalDelinquent / companies.length) * 100).toFixed(1)}% of all companies
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Overdue Revenue</CardTitle>
          <DollarSign className="h-4 w-4 text-orange-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-orange-600">
            {formatCurrency(overdueRevenue)}
          </div>
          <p className="text-xs text-muted-foreground">
            {overdueCount} accounts overdue
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Collection Rate</CardTitle>
          <Calendar className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-green-600">
            {(((companies.length - totalDelinquent) / companies.length) * 100).toFixed(1)}%
          </div>
          <p className="text-xs text-muted-foreground">
            On-time payment rate
          </p>
        </CardContent>
      </Card>
    </div>
  );
}