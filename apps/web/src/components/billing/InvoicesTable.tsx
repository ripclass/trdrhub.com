/**
 * InvoicesTable component - displays invoices with actions and filtering
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
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronRight as ChevronRightIcon,
  Download,
  CreditCard,
  Eye,
  MoreHorizontal,
  FileText,
  AlertCircle,
  CheckCircle,
  Clock
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { formatCurrency, getInvoiceStatusColor } from '@/types/billing';
import {
  useInvoices,
  useDownloadInvoice,
  useRetryPayment
} from '@/hooks/useBilling';
import type {
  InvoicesFilters,
  Invoice,
  InvoiceStatus,
  InvoiceLineItem
} from '@/types/billing';

interface InvoicesTableProps {
  className?: string;
  initialFilters?: InvoicesFilters;
  onInvoiceClick?: (invoice: Invoice) => void;
  showActions?: boolean;
  compact?: boolean;
}

export function InvoicesTable({
  className,
  initialFilters = {},
  onInvoiceClick,
  showActions = true,
  compact = false
}: InvoicesTableProps) {
  const [filters, setFilters] = useState<InvoicesFilters>({
    page: 1,
    per_page: compact ? 5 : 20,
    ...initialFilters
  });

  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const { data: invoicesData, isLoading, error, refetch } = useInvoices(filters);
  const downloadInvoice = useDownloadInvoice();
  const retryPayment = useRetryPayment();

  const getStatusIcon = (status: InvoiceStatus) => {
    switch (status) {
      case 'PAID':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'PENDING':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      case 'OVERDUE':
      case 'FAILED':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      default:
        return <FileText className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusDisplay = (status: InvoiceStatus) => {
    switch (status) {
      case 'PAID':
        return 'Paid';
      case 'PENDING':
        return 'Pending';
      case 'OVERDUE':
        return 'Overdue';
      case 'FAILED':
        return 'Failed';
      case 'CANCELLED':
        return 'Cancelled';
      default:
        return status;
    }
  };

  const handleFilterChange = (key: keyof InvoicesFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: key !== 'page' ? 1 : value
    }));
  };

  const handlePageChange = (page: number) => {
    handleFilterChange('page', page);
  };

  const handleRowExpand = (invoiceId: string) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(invoiceId)) {
        newSet.delete(invoiceId);
      } else {
        newSet.add(invoiceId);
      }
      return newSet;
    });
  };

  const handleDownloadInvoice = (invoiceId: string) => {
    downloadInvoice.mutate(invoiceId);
  };

  const handleRetryPayment = (invoiceId: string) => {
    retryPayment.mutate({ invoiceId });
  };

  const canRetryPayment = (status: InvoiceStatus) => {
    return status === 'FAILED' || status === 'OVERDUE';
  };

  const totalPages = invoicesData ? Math.ceil(invoicesData.total / (filters.per_page || 20)) : 0;
  const currentPage = filters.page || 1;

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center py-8">
          <p className="text-sm text-muted-foreground">
            Error loading invoices. Please try again.
          </p>
          <Button variant="outline" onClick={() => refetch()} className="mt-2">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <CardTitle className="flex items-center gap-2">
            Invoices
            {invoicesData && (
              <Badge variant="secondary">
                {invoicesData.total} total
              </Badge>
            )}
          </CardTitle>

          {!compact && (
            <div className="flex items-center space-x-2">
              {/* Status filter */}
              <Select
                value={filters.status || 'all'}
                onValueChange={(value) =>
                  handleFilterChange('status', value === 'all' ? undefined : value as InvoiceStatus)
                }
              >
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="PENDING">Pending</SelectItem>
                  <SelectItem value="PAID">Paid</SelectItem>
                  <SelectItem value="OVERDUE">Overdue</SelectItem>
                  <SelectItem value="FAILED">Failed</SelectItem>
                  <SelectItem value="CANCELLED">Cancelled</SelectItem>
                </SelectContent>
              </Select>

              {/* Per page selector */}
              <Select
                value={filters.per_page?.toString() || '20'}
                onValueChange={(value) => handleFilterChange('per_page', parseInt(value))}
              >
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10 per page</SelectItem>
                  <SelectItem value="20">20 per page</SelectItem>
                  <SelectItem value="50">50 per page</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: compact ? 3 : 5 }).map((_, i) => (
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
        ) : invoicesData?.invoices.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-sm text-muted-foreground">
              No invoices found.
            </p>
          </div>
        ) : (
          <>
            {/* Table */}
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    {!compact && <TableHead className="w-[50px]"></TableHead>}
                    <TableHead>Invoice</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Due Date</TableHead>
                    {showActions && <TableHead className="w-[50px]"></TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoicesData?.invoices.map((invoice) => (
                    <React.Fragment key={invoice.id}>
                      <TableRow
                        className={cn(
                          'group',
                          onInvoiceClick && 'cursor-pointer hover:bg-muted/50'
                        )}
                        onClick={() => onInvoiceClick?.(invoice)}
                      >
                        {!compact && (
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRowExpand(invoice.id);
                              }}
                            >
                              {expandedRows.has(invoice.id) ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRightIcon className="h-4 w-4" />
                              )}
                            </Button>
                          </TableCell>
                        )}

                        <TableCell>
                          <div>
                            <div className="font-medium">{invoice.invoice_number}</div>
                            <div className="text-sm text-muted-foreground">
                              {format(new Date(invoice.issued_date), 'MMM dd, yyyy')}
                            </div>
                          </div>
                        </TableCell>

                        <TableCell>
                          <div className="font-medium">
                            {formatCurrency(invoice.amount, invoice.currency)}
                          </div>
                        </TableCell>

                        <TableCell>
                          <div className="flex items-center space-x-2">
                            {getStatusIcon(invoice.status)}
                            <Badge
                              variant={invoice.status === 'PAID' ? 'default' :
                                      invoice.status === 'PENDING' ? 'secondary' : 'destructive'}
                              className={getInvoiceStatusColor(invoice.status)}
                            >
                              {getStatusDisplay(invoice.status)}
                            </Badge>
                          </div>
                        </TableCell>

                        <TableCell>
                          <div className={cn(
                            'text-sm',
                            invoice.status === 'OVERDUE' && 'text-red-600 font-medium'
                          )}>
                            {format(new Date(invoice.due_date), 'MMM dd, yyyy')}
                          </div>
                        </TableCell>

                        {showActions && (
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onInvoiceClick?.(invoice);
                                  }}
                                >
                                  <Eye className="h-4 w-4 mr-2" />
                                  View Details
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDownloadInvoice(invoice.id);
                                  }}
                                >
                                  <Download className="h-4 w-4 mr-2" />
                                  Download PDF
                                </DropdownMenuItem>
                                {canRetryPayment(invoice.status) && (
                                  <>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleRetryPayment(invoice.id);
                                      }}
                                    >
                                      <CreditCard className="h-4 w-4 mr-2" />
                                      Retry Payment
                                    </DropdownMenuItem>
                                  </>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        )}
                      </TableRow>

                      {/* Expandable row content */}
                      {!compact && expandedRows.has(invoice.id) && (
                        <TableRow>
                          <TableCell colSpan={showActions ? 6 : 5} className="p-0">
                            <Collapsible open={expandedRows.has(invoice.id)}>
                              <CollapsibleContent>
                                <div className="p-4 bg-muted/30">
                                  <InvoiceLineItems lineItems={invoice.line_items} />
                                </div>
                              </CollapsibleContent>
                            </Collapsible>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {!compact && totalPages > 1 && (
              <div className="flex items-center justify-between pt-4">
                <div className="text-sm text-muted-foreground">
                  Showing {((currentPage - 1) * (filters.per_page || 20)) + 1} to{' '}
                  {Math.min(currentPage * (filters.per_page || 20), invoicesData?.total || 0)} of{' '}
                  {invoicesData?.total || 0} results
                </div>

                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>

                  <div className="flex items-center space-x-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      const page = i + 1;
                      return (
                        <Button
                          key={page}
                          variant={currentPage === page ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => handlePageChange(page)}
                          className="w-8 h-8 p-0"
                        >
                          {page}
                        </Button>
                      );
                    })}
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
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

// Line items component
function InvoiceLineItems({ lineItems }: { lineItems: InvoiceLineItem[] }) {
  if (!lineItems || lineItems.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No line items available.</p>
    );
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-medium">Invoice Line Items</h4>
      <div className="space-y-2">
        {lineItems.map((item) => (
          <div key={item.id} className="flex items-center justify-between py-2 border-b last:border-b-0">
            <div className="flex-1">
              <div className="text-sm font-medium">{item.description}</div>
              {item.quantity > 1 && (
                <div className="text-xs text-muted-foreground">
                  {item.quantity} × {formatCurrency(item.unit_price)}
                </div>
              )}
            </div>
            <div className="text-sm font-medium">
              {formatCurrency(item.amount)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Compact version for dashboard overview
export function InvoicesTableCompact({
  className,
  maxRows = 5
}: {
  className?: string;
  maxRows?: number;
}) {
  return (
    <InvoicesTable
      className={className}
      initialFilters={{
        page: 1,
        per_page: maxRows
      }}
      showActions={false}
      compact={true}
    />
  );
}